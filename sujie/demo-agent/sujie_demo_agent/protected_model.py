"""One guarded model interface for Host, classification, analysis and child roles."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from dataclasses import asdict

from sujie_gateway.model_context import (
    ContextError,
    ContextSource,
    ModelEgressPolicy,
    build_effective_snapshot,
    build_snapshot,
    canonical,
    contains_protected,
    digest,
    safe_path,
)

from .bailian_agent import (
    ChatModel,
    ModelProtocolError,
    PreparedModelRequest,
    ProviderCompletion,
    ProviderResponseEvidence,
    supports_prepared_requests,
)
from .model_budget import BudgetError, ModelBudget
from .tokenizer_mapper import LocalTokenMapper

PURPOSES = frozenset({"MAIN", "CLASSIFY", "ISOLATED_ANALYSIS", "SUBAGENT", "RECOVERY"})


class ProtectedModel:
    """Bound by trusted Python configuration, never by model-supplied annotations."""

    def __init__(
        self,
        model: ChatModel,
        gateway,
        *,
        protected_values: tuple[str, ...] = (),
        purpose: str = "MAIN",
        tokenizer: LocalTokenMapper | None = None,
        budget: ModelBudget | None = None,
    ):
        if purpose not in PURPOSES:
            raise ValueError("INVALID_MODEL_PURPOSE")
        self._model, self.gateway, self.purpose = model, gateway, purpose
        self.policy = ModelEgressPolicy(protected_values=protected_values)
        self.tokenizer = tokenizer
        self.budget = budget or ModelBudget()
        self.forwarded_requests = 0
        self.blocked_requests = 0
        self.response_blocks = 0
        self.response_artifacts: tuple[str, ...] | None = None
        self.response_event_id: str | None = None
        self._assistant_bindings: dict[tuple[int, str, str], tuple[str, ...]] = {}

    @property
    def model(self):
        return getattr(self._model, "model", "scripted-test-model")

    @property
    def max_tokens(self):
        return getattr(self._model, "max_tokens", 512)

    @property
    def usage(self):
        return getattr(self._model, "usage", [])

    def for_purpose(self, purpose: str) -> ProtectedModel:
        return ProtectedModel(
            self._model,
            self.gateway,
            protected_values=self.policy.protected_values,
            purpose=purpose,
            tokenizer=self.tokenizer,
            budget=self.budget,
        )

    def _sources(self) -> tuple[ContextSource, ...]:
        return tuple(
            ContextSource(
                identifier,
                self.gateway.trace.artifact_contents[identifier],
                self.gateway.trace.artifacts[identifier].to_dict()["confidentiality"],
                self.gateway.trace.artifacts[identifier].to_dict()["origin"]["type"],
                tuple(self.gateway.trace.artifacts[identifier].to_dict()["allowed_uses"]),
                tuple(self.gateway.trace.artifacts[identifier].to_dict()["forbidden_uses"]),
            )
            for identifier in sorted(self.gateway._exposed_artifacts)
        )

    def _emit(self, event: str, payload: dict, artifacts=(), *, parents=None) -> str:
        return self.gateway.trace.emit(
            event,
            actor_id=self.gateway.grant.to_dict()["subject_id"],
            parents=parents
            if parents is not None
            else ([self.gateway._last_exposure_event] if self.gateway._last_exposure_event else []),
            artifact_ids=list(artifacts),
            payload={"purpose": self.purpose, **payload},
        )

    @staticmethod
    def _prefixes(messages: list[dict]) -> list[str]:
        prefix = hashlib.sha256(b"sujie-conversation-prefix-v1")
        result = []
        for message in messages:
            result.append(prefix.hexdigest())
            raw = canonical(message).encode("utf-8")
            prefix.update(str(len(raw)).encode() + b":" + raw)
        result.append(prefix.hexdigest())
        return result

    @staticmethod
    def _field_metadata(snapshot):
        return [
            {
                "field_index": item.index,
                "path": safe_path(item.path),
                "characters": len(item.text),
                "source_spans": [asdict(span) for span in item.spans],
                "inherited_artifacts": list(item.inherited_artifacts),
            }
            for item in snapshot.fields
        ]

    @staticmethod
    def _safe_provider_code(error: ModelProtocolError) -> str:
        code = str(error)
        if re.fullmatch(
            r"(?:BAILIAN_HTTP_[0-9]{3}|BAILIAN_(?:TRANSPORT_ERROR|RESPONSE_INVALID)|"
            r"MODEL_(?:OUTPUT_CREDENTIAL|CONFIG_INVALID|BINDING_(?:INVALID|INPUT_CHANGED|RECEIPT_MISMATCH)))",
            code,
        ):
            return code
        return "MODEL_PROTOCOL_ERROR"

    @staticmethod
    def _safe_context_code(error: ContextError) -> str:
        code = str(error)
        if re.fullmatch(
            r"MODEL_(?:CONTEXT_(?:INVALID|LIMIT|DEPTH_LIMIT|SIZE_LIMIT)|"
            r"SOURCE_(?:INVALID|SPAN_LIMIT)|EGRESS_(?:PROTECTED_VALUE|CLASSIFICATION|PURPOSE)|"
            r"OUTPUT_PROTECTED_VALUE|"
            r"BINDING_(?:INVALID|INPUT_CHANGED)|CONFIG_INVALID|"
            r"TOKEN(?:IZER_MISMATCH|_OFFSETS_INVALID))",
            code,
        ):
            return code
        return "MODEL_PROTOCOL_ERROR"

    async def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        call_id = uuid.uuid4().hex
        self.response_artifacts = self.response_event_id = None
        prepared = effective = None
        try:
            sources = self._sources()
            prefixes = self._prefixes(messages)
            # Unknown rewrites inherit current exposure. Observed responses bind
            # to their original request and validated conversation prefix.
            inherited = {
                index: self._assistant_bindings.get(
                    (index, digest(canonical(message)), prefixes[index]),
                    tuple(source.artifact_id for source in sources),
                )
                for index, message in enumerate(messages)
                if message.get("role") == "assistant"
            }
            snapshot = build_snapshot(
                messages, tools, sources=sources, inherited_by_message=inherited
            )
            self.policy.check(snapshot)
            if supports_prepared_requests(self._model):
                audited = snapshot.payload()
                prepared = self._model.prepare_request(audited["messages"], audited["tools"])
                if not isinstance(prepared, PreparedModelRequest):
                    raise ContextError("MODEL_BINDING_INVALID")
                effective = build_effective_snapshot(snapshot, prepared.wire_json)
                self.policy.check(effective)
                output_allowance = effective.payload().get("max_tokens")
            else:
                output_allowance = self.max_tokens
            if type(output_allowance) is not int or not 0 <= output_allowance <= 2048:
                raise ContextError("MODEL_CONFIG_INVALID")
            mapping = (
                self.tokenizer.map(effective or snapshot)
                if self.tokenizer
                else {
                    "status": "UNAVAILABLE",
                    "provider_tokenization": "UNKNOWN",
                    "fields": [],
                }
            )
        except (ContextError, ModelProtocolError) as error:
            self.blocked_requests += 1
            code = (
                self._safe_context_code(error)
                if isinstance(error, ContextError)
                else self._safe_provider_code(error)
            )
            # Provider credential refusal is safe and occurs before client creation.
            if isinstance(error, ModelProtocolError) and str(error) == "MODEL_EGRESS_CREDENTIAL":
                code = "MODEL_EGRESS_CREDENTIAL"
            self._emit(
                "MODEL_EGRESS_BLOCKED", {"call_id": call_id, "code": code, "direction": "REQUEST"}
            )
            raise ModelProtocolError(code) from None
        request_artifacts = (effective or snapshot).referenced_artifacts
        binding = {
            "call_id": call_id,
            "request_hash": snapshot.request_hash,
            "request_hash_scope": "MESSAGES_TOOLS_CANONICAL_JSON",
            "binding_scope": "HTTP_JSON_BODY" if effective else "MESSAGES_TOOLS_ONLY",
            "effective_request_hash": effective.request_hash if effective else None,
            "effective_request_bytes": len(effective.wire_json.encode("utf-8"))
            if effective
            else None,
        }
        try:
            # Local estimate only; opaque provider tokenization/billing is unknown.
            units = len((effective or snapshot).wire_json.encode("utf-8")) + output_allowance + 512
            ticket = self.budget.reserve(self.purpose, units)
        except BudgetError as error:
            self.blocked_requests += 1
            self._emit(
                "MODEL_EGRESS_BLOCKED", {**binding, "code": str(error), "direction": "REQUEST"}
            )
            raise ModelProtocolError(str(error)) from None
        binding["budget_ticket"] = ticket
        request_event = self._emit(
            "MODEL_REQUEST_CHECKED",
            {
                **binding,
                "fields": self._field_metadata(snapshot),
                "effective_fields": self._field_metadata(effective) if effective else [],
                "token_mapping": {
                    **mapping,
                    "scope": "HTTP_JSON_BODY_STRING_FIELDS"
                    if effective
                    else "MESSAGES_TOOLS_STRING_FIELDS",
                },
                "assistant_lineage": "REQUEST_BOUND_WITH_PREFIX_VALIDATION",
            },
            request_artifacts,
        )
        self.forwarded_requests += 1
        usage_before = len(self.usage)
        status, failure_code = "FAILED", "MODEL_BACKEND_FAILED"
        completion = evidence = None
        try:
            if prepared is not None:
                completion = await self._model.complete_prepared(prepared.bind(call_id, ticket))
                if not isinstance(completion, ProviderCompletion):
                    raise ModelProtocolError("MODEL_BINDING_RECEIPT_MISMATCH")
                evidence = completion.evidence
                if (
                    not isinstance(evidence, ProviderResponseEvidence)
                    or evidence.effective_request_hash != effective.request_hash
                    or evidence.call_id != call_id
                    or evidence.budget_ticket != ticket
                    or evidence.message_hash != digest(completion.message_json)
                ):
                    evidence = None
                    raise ModelProtocolError("MODEL_BINDING_RECEIPT_MISMATCH")
                response = completion.message()
                body_message = json.loads(completion.body_json)["choices"][0]["message"]
                if canonical(body_message) != completion.message_json:
                    raise ModelProtocolError("MODEL_BINDING_RECEIPT_MISMATCH")
            else:
                audited = snapshot.payload()
                response = await self._model.complete(audited["messages"], audited["tools"])
            status = "RETURNED"
        except asyncio.CancelledError:
            status, failure_code = "CANCELLED", "MODEL_CALL_CANCELLED"
            raise
        except ModelProtocolError as error:
            failure_code = self._safe_provider_code(error)
            candidate = error.evidence
            if (
                isinstance(candidate, ProviderResponseEvidence)
                and effective is not None
                and candidate.effective_request_hash == effective.request_hash
                and candidate.call_id == call_id
                and candidate.budget_ticket == ticket
            ):
                evidence = candidate
            raise ModelProtocolError(failure_code) from None
        except Exception:
            raise ModelProtocolError(failure_code) from None
        finally:
            if evidence is not None:
                reported_tokens = evidence.reported_tokens
            else:
                reported = []
                for row in self.usage[usage_before:]:
                    value = row.get("total_tokens") if isinstance(row, dict) else None
                    if type(value) is int and 0 <= value <= 1_000_000_000:
                        reported.append(value)
                    else:
                        reported = []
                        break
                reported_tokens = sum(reported) if reported else None
            try:
                self.budget.settle(ticket, status=status, reported_tokens=reported_tokens)
            except BudgetError as error:
                raise ModelProtocolError(str(error)) from None
            if status != "RETURNED":
                self._emit(
                    "MODEL_EGRESS_BLOCKED",
                    {
                        **binding,
                        "code": failure_code,
                        "direction": "RESPONSE",
                        "call_status": status,
                        "provider_receipt": evidence.metadata() if evidence else None,
                    },
                    request_artifacts,
                    parents=[request_event],
                )
        response_json = None
        try:
            # Snapshot the returned message before giving a fresh copy to callers.
            response_json = canonical(response)
            if not isinstance(response, dict):
                raise ContextError("MODEL_CONTEXT_INVALID")
            forbidden = self.policy.protected_values + tuple(
                source.text
                for source in self._sources()
                if source.confidentiality not in self.policy.allowed_confidentialities
            )
            inspected = json.loads(completion.body_json) if completion else response
            if contains_protected(response, forbidden) or contains_protected(inspected, forbidden):
                raise ContextError("MODEL_OUTPUT_PROTECTED_VALUE")
        except ContextError as error:
            self.response_blocks += 1
            self._emit(
                "MODEL_EGRESS_BLOCKED",
                {
                    **binding,
                    "code": self._safe_context_code(error),
                    "direction": "RESPONSE",
                    "call_status": status,
                    "response_hash": digest(response_json) if response_json is not None else None,
                    "response_hash_scope": "CANONICAL_RETURNED_MESSAGE_JSON",
                    "response_hash_status": "CAPTURED"
                    if response_json is not None
                    else "UNAVAILABLE",
                    "provider_receipt": evidence.metadata() if evidence else None,
                },
                request_artifacts,
                parents=[request_event],
            )
            raise ModelProtocolError(self._safe_context_code(error)) from None
        self.response_event_id = self._emit(
            "MODEL_RESPONSE_CHECKED",
            {
                **binding,
                "code": "RESPONSE_ACCEPTED",
                "call_status": status,
                "response_hash": digest(response_json),
                "response_hash_scope": "CANONICAL_RETURNED_MESSAGE_JSON",
                "response_hash_status": "CAPTURED",
                "provider_receipt": evidence.metadata() if evidence else None,
                "raw_response_status": evidence.raw_response_status if evidence else "UNAVAILABLE",
            },
            request_artifacts,
            parents=[request_event],
        )
        response = json.loads(response_json)
        content = response.get("content") or ""
        calls = response.get("tool_calls") or []
        if isinstance(content, str) and isinstance(calls, list):
            normalized = {"role": "assistant", "content": content}
            if calls:
                normalized["tool_calls"] = calls
            audited_messages = snapshot.payload()["messages"]
            self._assistant_bindings[
                len(audited_messages),
                digest(canonical(normalized)),
                self._prefixes(audited_messages)[-1],
            ] = request_artifacts
        self.response_artifacts = request_artifacts
        return response
