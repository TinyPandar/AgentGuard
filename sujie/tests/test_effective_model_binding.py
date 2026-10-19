"""HTTP capture checks the whole admitted body and local response/budget correlation."""

import asyncio
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from evaluation_models import calibration_backend
from paired_runtime import RecordedModel
from sujie_demo_agent.bailian_agent import (
    BailianChatModel,
    BailianCredentials,
    ModelProtocolError,
    ProviderCompletion,
)
from sujie_demo_agent.model_budget import ModelBudget
from sujie_demo_agent.protected_model import PURPOSES, ProtectedModel
from sujie_gateway.model_context import canonical, digest, encoded_variants

KEY = "sk-synthetic-effective-binding-not-a-real-key-123456"
ENDPOINT = "https://offline-model.invalid/compatible-mode/v1"
MESSAGES = [{"role": "user", "content": '核对🙂\\n"quoted" русский'}]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inspect",
            "description": "只读检查",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]


class Trace:
    def __init__(self):
        self.artifacts, self.artifact_contents, self.events, self.payloads = {}, {}, [], {}

    def emit(self, event, *, actor_id, parents, artifact_ids, payload):
        identifier = f"event-{len(self.events)}"
        self.events.append({"event_type": event, "event_id": identifier, "parents": parents})
        self.payloads[identifier] = payload
        return identifier


def gateway():
    return SimpleNamespace(
        trace=Trace(),
        grant=SimpleNamespace(to_dict=lambda: {"subject_id": "synthetic-host"}),
        _last_exposure_event=None,
        _exposed_artifacts=set(),
    )


def metadata(context, event_type):
    return [
        context.trace.payloads[event["event_id"]]
        for event in context.trace.events
        if event["event_type"] == event_type
    ]


@pytest.fixture
def budget():
    item = ModelBudget(max_requests=20, max_units=1_000_000)
    yield item
    item.ledger.close()


@pytest.fixture
def transport(monkeypatch):
    client_type = httpx.AsyncClient
    captured = []

    def install(handler=None):
        async def respond(request):
            captured.append(request)
            if handler is not None:
                response = handler(request)
                return await response if hasattr(response, "__await__") else response
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "已核对🙂"}}],
                    "usage": {"total_tokens": 7},
                },
            )

        def client(*args, **kwargs):
            return client_type(*args, transport=httpx.MockTransport(respond), **kwargs)

        monkeypatch.setattr("sujie_demo_agent.bailian_agent.httpx.AsyncClient", client)
        return captured

    return install


def provider(**config):
    return BailianChatModel(BailianCredentials(KEY, ENDPOINT), **config)


@pytest.mark.parametrize("purpose", sorted(PURPOSES))
@pytest.mark.parametrize("tools", [[], TOOLS], ids=["no-tools", "tools"])
async def test_every_guarded_purpose_attests_exact_unicode_http_body_and_response(
    purpose, tools, transport, budget
):
    captured, context = transport(), gateway()
    guarded = ProtectedModel(provider(), context, purpose=purpose, budget=budget)
    answer = await guarded.complete(MESSAGES, tools)
    checked = metadata(context, "MODEL_REQUEST_CHECKED")[0]
    returned = metadata(context, "MODEL_RESPONSE_CHECKED")[0]
    sent = captured[0].content
    body = json.loads(sent)
    assert body["messages"] == MESSAGES
    assert body["model"] == "qwen-plus-2025-12-01"
    assert body["max_tokens"] == 512 and body["temperature"] == 0
    assert b"\\u6838" not in sent and "🙂".encode() in sent
    assert ("tools" in body) == bool(tools)
    assert ("tool_choice" in body) == bool(tools)
    assert checked["request_hash"] == digest(canonical({"messages": MESSAGES, "tools": tools}))
    assert checked["effective_request_hash"] == "sha256:" + hashlib.sha256(sent).hexdigest()
    assert checked["binding_scope"] == "HTTP_JSON_BODY"
    assert checked["token_mapping"]["scope"] == "HTTP_JSON_BODY_STRING_FIELDS"
    assert any(field["path"] == ["model"] for field in checked["effective_fields"])
    assert returned["call_id"] == checked["call_id"]
    assert returned["budget_ticket"] == checked["budget_ticket"]
    assert returned["response_hash"] == digest(canonical(answer))
    assert returned["provider_receipt"]["sent_request_hash"] == checked["effective_request_hash"]
    assert returned["provider_receipt"]["raw_response_status"] == "CAPTURED"
    row = budget.ledger.connection.execute(
        "SELECT id,purpose,status,reported_tokens FROM model_reservations"
    ).fetchone()
    assert row == (checked["budget_ticket"], purpose, "RETURNED", 7)
    assert KEY not in json.dumps(context.trace.payloads)
    assert captured[0].headers["authorization"] == "Bearer " + KEY


@pytest.mark.parametrize(
    "change",
    [
        {"model": "qwen-another-snapshot"},
        {"max_tokens": 768},
        {"temperature": 1.5},
        {"tool_choice": {"type": "function", "function": {"name": "inspect"}}},
    ],
)
async def test_config_changes_effective_hash_without_redefining_legacy_hash(
    change, transport, budget
):
    transport()
    context = gateway()
    for config in ({}, change):
        await ProtectedModel(provider(**config), context, budget=budget).complete(MESSAGES, TOOLS)
    first, second = metadata(context, "MODEL_REQUEST_CHECKED")
    assert first["request_hash"] == second["request_hash"]
    assert first["effective_request_hash"] != second["effective_request_hash"]


async def test_no_config_or_input_mutation_after_policy_can_change_sent_bytes(transport, budget):
    captured, context, backend = transport(), gateway(), provider()
    messages, tools = json.loads(canonical(MESSAGES)), json.loads(canonical(TOOLS))
    expected = backend.prepare_request(messages, tools).wire_json.encode()

    class MutatingMapper:
        def map(self, snapshot):
            assert snapshot.wire_json.encode() == expected
            messages[0]["content"] = KEY
            tools[0]["function"]["description"] = KEY
            backend.model, backend.max_tokens = "qwen-mutated-after-policy", 2048
            backend.temperature, backend.tool_choice = 1.8, {"uninspected": KEY}
            backend._credentials.api_key = "sk-mutated-after-policy-not-original-key"
            backend._credentials.base_url = "https://must-not-contact.invalid"
            backend.timeout = 0.01
            return {"status": "LOCAL_TEST_MAPPING", "fields": []}

    await ProtectedModel(backend, context, tokenizer=MutatingMapper(), budget=budget).complete(
        messages, tools
    )
    assert captured[0].content == expected
    assert str(captured[0].url) == ENDPOINT + "/chat/completions"
    assert captured[0].headers["authorization"] == "Bearer " + KEY
    reservation = budget.ledger.connection.execute(
        "SELECT reserved FROM model_reservations"
    ).fetchone()
    assert reservation == (len(expected) + 512 + 512,)
    assert KEY not in json.dumps(context.trace.payloads)


async def test_mutation_during_await_cannot_rebuild_body(transport, budget):
    captured, entered, release = transport(), asyncio.Event(), asyncio.Event()

    class WaitingProvider(BailianChatModel):
        async def complete_prepared(self, prepared):
            entered.set()
            await release.wait()
            return await super().complete_prepared(prepared)

    backend = WaitingProvider(BailianCredentials(KEY, ENDPOINT))
    context = gateway()
    messages = json.loads(canonical(MESSAGES))
    running = asyncio.create_task(
        ProtectedModel(backend, context, budget=budget).complete(messages, [])
    )
    await asyncio.wait_for(entered.wait(), 2)
    backend.model, backend.max_tokens, backend.temperature = "qwen-later", 1024, 1
    messages[0]["content"] = KEY
    release.set()
    await running
    body = json.loads(captured[0].content)
    assert body["model"] == "qwen-plus-2025-12-01" and body["max_tokens"] == 512
    assert body["temperature"] == 0 and body["messages"] == MESSAGES


@pytest.mark.parametrize("what", ["messages", "tools"])
async def test_preparation_cannot_swap_inputs_or_drop_tools(what, transport, budget):
    captured, context = transport(), gateway()

    class SwappingProvider(BailianChatModel):
        def prepare_request(self, messages, tools):
            if what == "messages":
                messages[0]["content"] = "provider rewrote the inspected message"
            else:
                tools = []
            return super().prepare_request(messages, tools)

    with pytest.raises(ModelProtocolError, match="MODEL_BINDING_INPUT_CHANGED"):
        await ProtectedModel(
            SwappingProvider(BailianCredentials(KEY, ENDPOINT)), context, budget=budget
        ).complete(MESSAGES, TOOLS)
    assert captured == [] and budget.view()["requests_reserved"] == 0
    assert metadata(context, "MODEL_REQUEST_CHECKED") == []


@pytest.mark.parametrize("location", ["model", "tool_choice", "extra_value", "extra_key"])
async def test_all_effective_strings_and_keys_receive_sensitive_value_policy(
    location, transport, budget
):
    captured, context = transport(), gateway()
    secret = "SYNTHETIC-PRIVATE-CONFIG-TEXT-12345"

    class ExtraProvider(BailianChatModel):
        def prepare_request(self, messages, tools):
            prepared = super().prepare_request(messages, tools)
            payload = json.loads(prepared.wire_json)
            if location == "extra_value":
                payload["unexpected_provider_option"] = {"nested": secret}
            elif location == "extra_key":
                payload[secret] = "public"
            return replace(prepared, wire_json=canonical(payload))

    backend = ExtraProvider(
        BailianCredentials(KEY, ENDPOINT),
        model="qwen-" + secret if location == "model" else "qwen-synthetic",
        tool_choice={"type": "function", "function": {"name": secret}}
        if location == "tool_choice"
        else "auto",
    )
    with pytest.raises(ModelProtocolError, match="MODEL_EGRESS_PROTECTED_VALUE"):
        await ProtectedModel(backend, context, protected_values=(secret,), budget=budget).complete(
            MESSAGES, TOOLS
        )
    assert captured == [] and budget.view()["requests_reserved"] == 0
    public = json.dumps(context.trace.payloads)
    assert all(value not in public for value in encoded_variants(secret))


@pytest.mark.parametrize("location", ["model", "tool_choice"])
@pytest.mark.parametrize("encoded", [False, True])
async def test_provider_credentials_in_configuration_are_refused_before_transport(
    location, encoded, transport, budget
):
    captured, context = transport(), gateway()
    value = KEY.encode().hex() if encoded else KEY
    backend = provider(
        model="qwen-" + value if location == "model" else "qwen-synthetic",
        tool_choice={"function": {"name": value}} if location == "tool_choice" else "auto",
    )
    with pytest.raises(ModelProtocolError, match="MODEL_EGRESS_CREDENTIAL"):
        await ProtectedModel(backend, context, budget=budget).complete(MESSAGES, TOOLS)
    assert captured == [] and budget.view()["requests_reserved"] == 0
    assert all(value not in json.dumps(context.trace.payloads) for value in encoded_variants(KEY))


async def test_message_and_http_body_hashes_have_distinct_scopes(transport, budget):
    raw_bodies = []

    def respond(request):
        index = len(raw_bodies)
        message = {"content": "相同🙂" if index < 2 else "另一个回答🙂"}
        raw = json.dumps(
            {"choices": [{"message": message}], "request_id": str(index)},
            ensure_ascii=False,
            indent=index + 1,
        ).encode()
        raw_bodies.append(raw)
        return httpx.Response(200, content=raw)

    transport(respond)
    context, guarded = gateway(), None
    guarded = ProtectedModel(provider(), context, budget=budget)
    for _ in range(3):
        await guarded.complete(MESSAGES, [])
    rows = metadata(context, "MODEL_RESPONSE_CHECKED")
    assert rows[0]["response_hash"] == rows[1]["response_hash"] != rows[2]["response_hash"]
    for row, raw in zip(rows, raw_bodies, strict=True):
        receipt = row["provider_receipt"]
        assert receipt["raw_response_hash"] == "sha256:" + hashlib.sha256(raw).hexdigest()
        assert receipt["raw_response_hash_scope"] == "HTTPX_DECODED_RESPONSE_BODY_BYTES"
    assert len({row["provider_receipt"]["raw_response_hash"] for row in rows}) == 3
    assert len({row["call_id"] for row in rows}) == 3


@pytest.mark.parametrize(
    "fault", ["http-error", "invalid-json", "envelope-credential", "envelope-private"]
)
async def test_rejected_response_has_hash_only_evidence_and_no_body_or_key(
    fault, transport, budget
):
    secret = "SYNTHETIC-PRIVATE-RESPONSE-ONLY-123456"
    raw = (
        ("provider failure body " + KEY).encode()
        if fault in {"http-error", "invalid-json"}
        else json.dumps(
            {
                "choices": [{"message": {"content": "public answer"}}],
                "ignored": {
                    KEY if fault == "envelope-credential" else "metadata": "public"
                    if fault == "envelope-credential"
                    else secret
                },
                "usage": {"total_tokens": 11},
            }
        ).encode()
    )
    transport(lambda request: httpx.Response(503 if fault == "http-error" else 200, content=raw))
    context = gateway()
    expected = {
        "http-error": "BAILIAN_HTTP_503",
        "invalid-json": "BAILIAN_RESPONSE_INVALID",
        "envelope-credential": "MODEL_OUTPUT_CREDENTIAL",
        "envelope-private": "MODEL_OUTPUT_PROTECTED_VALUE",
    }[fault]
    with pytest.raises(ModelProtocolError, match=expected) as error:
        await ProtectedModel(
            provider(), context, protected_values=(secret,), budget=budget
        ).complete(MESSAGES, [])
    refused = metadata(context, "MODEL_EGRESS_BLOCKED")[-1]
    checked = metadata(context, "MODEL_REQUEST_CHECKED")[0]
    assert refused["call_id"] == checked["call_id"]
    assert refused["budget_ticket"] == checked["budget_ticket"]
    assert (
        refused["provider_receipt"]["raw_response_hash"]
        == "sha256:" + hashlib.sha256(raw).hexdigest()
    )
    assert metadata(context, "MODEL_RESPONSE_CHECKED") == []
    assert KEY not in json.dumps(context.trace.payloads) + str(error.value)
    assert secret not in json.dumps(context.trace.payloads) + str(error.value)
    assert budget.view()["requests_reserved"] == 1 and budget.view()["pending_requests"] == 0
    assert budget.view()["reported_tokens"] == (11 if fault.startswith("envelope") else 0)
    assert budget.view()["unknown_usage_requests"] == (0 if fault.startswith("envelope") else 1)


@pytest.mark.parametrize("cancel", [False, True], ids=["transport-error", "cancelled"])
async def test_unknown_transport_and_cancellation_keep_full_reservation(cancel, transport, budget):
    entered = asyncio.Event()

    async def respond(request):
        entered.set()
        if cancel:
            await asyncio.Event().wait()
        raise httpx.ReadTimeout(KEY)

    transport(respond)
    context = gateway()
    guarded = ProtectedModel(provider(), context, budget=budget)
    pending = asyncio.create_task(guarded.complete(MESSAGES, []))
    await asyncio.wait_for(entered.wait(), 2)
    if cancel:
        pending.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else ModelProtocolError):
        await pending
    row = budget.ledger.connection.execute(
        "SELECT status,reserved,reported_tokens FROM model_reservations"
    ).fetchone()
    assert row[0] == ("CANCELLED" if cancel else "FAILED") and row[1] > 0 and row[2] is None
    assert budget.view()["charged_units"] == row[1]
    refused = metadata(context, "MODEL_EGRESS_BLOCKED")[-1]
    assert refused["call_status"] == row[0]
    assert (
        refused["provider_receipt"] is None
        or refused["provider_receipt"]["raw_response_status"] == "UNAVAILABLE"
    )
    assert KEY not in json.dumps(context.trace.payloads)


async def test_receipt_cannot_claim_another_request(transport, budget):
    transport()

    class WrongReceipt(BailianChatModel):
        async def complete_prepared(self, prepared):
            result = await super().complete_prepared(prepared)
            return ProviderCompletion(
                result.message_json,
                result.body_json,
                result.usage,
                replace(result.evidence, call_id="0" * 32),
            )

    context = gateway()
    with pytest.raises(ModelProtocolError, match="MODEL_BINDING_RECEIPT_MISMATCH"):
        await ProtectedModel(
            WrongReceipt(BailianCredentials(KEY, ENDPOINT)), context, budget=budget
        ).complete(MESSAGES, [])
    assert metadata(context, "MODEL_RESPONSE_CHECKED") == []
    assert budget.view()["pending_requests"] == 0


async def test_scripted_scope_stays_explicit_and_returned_message_is_frozen(budget):
    response = {"content": "public scripted response"}

    class Scripted:
        async def complete(self, messages, tools):
            return response

    context = gateway()
    actual = await ProtectedModel(Scripted(), context, budget=budget).complete(MESSAGES, [])
    response["content"] = "backend mutated shared object later"
    checked = metadata(context, "MODEL_REQUEST_CHECKED")[0]
    returned = metadata(context, "MODEL_RESPONSE_CHECKED")[0]
    assert checked["binding_scope"] == "MESSAGES_TOOLS_ONLY"
    assert checked["effective_request_hash"] is None and checked["effective_fields"] == []
    assert returned["provider_receipt"] is None and returned["raw_response_status"] == "UNAVAILABLE"
    assert actual["content"] == "public scripted response"
    assert returned["response_hash"] == digest(canonical(actual))


async def test_recorded_provider_passes_prepared_binding_and_detects_next_recipe_drift(
    transport, budget
):
    captured, models, context, backend = transport(), [], gateway(), provider()
    recorded = RecordedModel(backend, models)
    guarded = ProtectedModel(recorded, context, budget=budget)
    await guarded.complete(MESSAGES, TOOLS)
    row = models[0]["requests"][0]
    assert row["content_hash"] == digest(canonical({"messages": MESSAGES, "tools": TOOLS}))
    assert row["effective_request_hash"] == digest(captured[0].content.decode())
    assert row["provider_receipt"]["call_id"] == row["call_id"]
    assert row["provider_receipt"]["budget_ticket"] == row["budget_ticket"]
    backend.temperature = 1
    with pytest.raises(ValueError, match="PAIRED_MODEL_CONFIGURATION_DRIFT"):
        await guarded.complete(MESSAGES, TOOLS)
    assert len(captured) == 1 and budget.view()["requests_reserved"] == 1


async def test_configuration_source_lineage_uses_full_effective_snapshot(transport, budget):
    transport()
    context = gateway()
    source = "source-profile-tag"
    context.trace.artifact_contents["config-source"] = source
    context.trace.artifacts["config-source"] = SimpleNamespace(
        to_dict=lambda: {
            "confidentiality": "INTERNAL",
            "origin": {"type": "HOST_DATA"},
            "allowed_uses": ["ANALYZE"],
            "forbidden_uses": [],
        }
    )
    context._exposed_artifacts.add("config-source")
    guarded = ProtectedModel(provider(model="qwen-" + source), context, budget=budget)
    await guarded.complete(MESSAGES, [])
    checked = metadata(context, "MODEL_REQUEST_CHECKED")[0]
    assert not any(field["source_spans"] for field in checked["fields"])
    assert any(field["source_spans"] for field in checked["effective_fields"])
    assert guarded.response_artifacts == ("config-source",)


@pytest.mark.parametrize("profile", ["delegated-report", "memory-update"])
async def test_actual_nested_and_memory_http_paths_keep_full_binding(profile, transport):
    from paired_runtime import run_model_session
    from runtime_variants import TrialTaskSession
    from sujie_control.model_runner import ModelCoordinator
    from sujie_gateway.m1_runtime import new_id

    scripts, models = {}, []

    async def respond(request):
        body = json.loads(request.content)
        message = await scripts[body["model"]].complete(body["messages"], body.get("tools", []))
        return httpx.Response(
            200, json={"choices": [{"message": message}], "usage": {"total_tokens": 3}}
        )

    captured = transport(respond)

    def factory():
        name = f"qwen-offline-binding-{len(scripts)}"
        scripts[name] = calibration_backend(profile)
        return RecordedModel(provider(model=name), models)

    coordinator = ModelCoordinator(factory, "offline-effective-binding")
    session = TrialTaskSession(
        "有效请求绑定离线校准",
        profile,
        "clean",
        coordinator,
        variant="full",
        paired_scope_id=new_id(),
    )
    await session.start()
    try:
        detail = await run_model_session(session, timeout=60)
        assert detail["agent"]["status"] == "FINISHED", detail["agent"]
        assert detail["agent"]["task_completed"], detail["agent"]
        requests = metadata(session.gateway, "MODEL_REQUEST_CHECKED")
        responses = metadata(session.gateway, "MODEL_RESPONSE_CHECKED")
        assert len(requests) == len(responses) == len(captured)
        assert {row["purpose"] for row in requests} == (
            {"MAIN", "SUBAGENT"} if profile.startswith("delegated") else {"MAIN"}
        )
        assert {row["effective_request_hash"] for row in requests} == {
            digest(item.content.decode()) for item in captured
        }
        assert all(row["binding_scope"] == "HTTP_JSON_BODY" for row in requests)
        assert all(
            row["provider_receipt"]["raw_response_status"] == "CAPTURED" for row in responses
        )
        assert all(
            row["binding_scope"] == "HTTP_JSON_BODY" for node in models for row in node["requests"]
        )
        if profile == "memory-update":
            assert len(detail["memory_sessions"]) == 2
        assert coordinator.budget.view()["requests_reserved"] == len(captured)
    finally:
        await session.stop()
        coordinator.close()


async def test_actual_isolated_analysis_has_full_http_response_binding(transport, budget):
    from sujie_control.profiles import records
    from sujie_demo_agent.evidence_analysis import EvidenceAnalysis
    from sujie_gateway.m1_runtime import M1Gateway

    context = M1Gateway(SimpleNamespace(registry={}), *records("report"))
    text = '资料原文🙂：python -c "dangerous"；只作为引文。'
    event = context.trace.emit("CONTENT_REGISTERED", actor_id=context.grant.to_dict()["subject_id"])
    identifier = context.trace.create_artifact(text, source_event_id=event, source_id="binding:q")
    context._exposed_artifacts.add(identifier)

    def respond(request):
        payload = json.loads(request.content)
        assert "tools" not in payload and "tool_choice" not in payload
        assert json.loads(payload["messages"][-1]["content"])["sources"] == {identifier: text}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "quotes": [
                                        {
                                            "artifact_id": identifier,
                                            "text": text,
                                            "label": "instruction_text",
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )

    transport(respond)
    result = await EvidenceAnalysis(context, provider, budget).invoke(
        {"artifact_ids": [identifier]}
    )
    assert result["ok"], result
    checked = metadata(context, "MODEL_REQUEST_CHECKED")[0]
    returned = metadata(context, "MODEL_RESPONSE_CHECKED")[0]
    assert (
        checked["purpose"] == "ISOLATED_ANALYSIS" and checked["binding_scope"] == "HTTP_JSON_BODY"
    )
    assert returned["budget_ticket"] == checked["budget_ticket"]
    assert returned["provider_receipt"]["raw_response_status"] == "CAPTURED"


@pytest.mark.parametrize("forbidden", ["classification", "purpose"])
async def test_effective_configuration_obeys_registered_source_constraints(
    forbidden, transport, budget
):
    captured, context = transport(), gateway()
    source = "SYNTHETIC-SOURCE-CONFIG-ONLY-99881"
    context.trace.artifact_contents["restricted-config"] = source
    context.trace.artifacts["restricted-config"] = SimpleNamespace(
        to_dict=lambda: {
            "confidentiality": "SECRET" if forbidden == "classification" else "INTERNAL",
            "origin": {"type": "HOST_DATA"},
            "allowed_uses": ["ANALYZE"] if forbidden == "classification" else ["QUOTE"],
            "forbidden_uses": [],
        }
    )
    context._exposed_artifacts.add("restricted-config")
    with pytest.raises(ModelProtocolError, match="MODEL_EGRESS_" + forbidden.upper()):
        await ProtectedModel(provider(model="qwen-" + source), context, budget=budget).complete(
            MESSAGES, []
        )
    assert captured == [] and budget.view()["requests_reserved"] == 0
    assert source not in json.dumps(context.trace.payloads)


@pytest.mark.parametrize("at_prepare", [True, False])
async def test_arbitrary_backend_exception_text_cannot_enter_metadata(
    at_prepare, transport, budget
):
    from sujie_gateway.model_context import ContextError

    captured, context = transport(), gateway()

    class UnsafeErrorProvider(BailianChatModel):
        def prepare_request(self, messages, tools):
            if at_prepare:
                raise ContextError(KEY)
            return super().prepare_request(messages, tools)

        async def complete_prepared(self, prepared):
            raise ModelProtocolError(KEY)

    with pytest.raises(ModelProtocolError, match="MODEL_PROTOCOL_ERROR") as error:
        await ProtectedModel(
            UnsafeErrorProvider(BailianCredentials(KEY, ENDPOINT)), context, budget=budget
        ).complete(MESSAGES, [])
    assert captured == []
    assert KEY not in str(error.value) + json.dumps(context.trace.payloads)
    assert budget.view()["pending_requests"] == 0


def test_entrypoint_registry_matches_all_protected_constructors_and_excludes_legacy():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    registry = json.loads(
        (root / "eval/protocols/effective_model_entrypoints_development_v1.json").read_bytes()
    )
    assert registry["development_only"] and not registry["formal_evaluation_ready"]
    declared = {
        (row["path"], row["class"], row["method"], row["purpose"])
        for row in registry["protected_model_constructors"]
    }
    found = set()

    class Constructors(ast.NodeVisitor):
        class_name = method_name = None

        def visit_ClassDef(self, node):
            previous, self.class_name = self.class_name, node.name
            self.generic_visit(node)
            self.class_name = previous

        def visit_FunctionDef(self, node):
            previous, self.method_name = self.method_name, node.name
            self.generic_visit(node)
            self.method_name = previous

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == "ProtectedModel":
                value = next(
                    (item.value for item in node.keywords if item.arg == "purpose"),
                    ast.Constant("MAIN"),
                )
                purpose = (
                    value.value
                    if isinstance(value, ast.Constant)
                    else "caller-selected-supported-purpose"
                )
                found.add(
                    (path.relative_to(root).as_posix(), self.class_name, self.method_name, purpose)
                )
            self.generic_visit(node)

    for directory in ("control-plane-python", "demo-agent"):
        for path in (root / directory).rglob("*.py"):
            Constructors().visit(ast.parse(path.read_text("utf-8")))
    assert found == declared
    excluded = {row["path"] for row in registry["excluded_historical_bare_entrypoints"]}
    assert {
        "demo-agent/sujie_demo_agent/semantic_detector.py",
        "demo-agent/sujie_demo_agent/semantic_detector_v2.py",
    } <= excluded
    assert registry["scripted_backend_scope"] == "MESSAGES_TOOLS_ONLY"


async def test_provider_returned_message_must_match_received_envelope(transport, budget):
    transport()
    context = gateway()
    secret = "SYNTHETIC-PRIVATE-RETURN-ONLY-55001"

    class InconsistentProvider(BailianChatModel):
        async def complete_prepared(self, prepared):
            completion = await super().complete_prepared(prepared)
            message_json = canonical({"content": secret})
            return replace(
                completion,
                message_json=message_json,
                evidence=replace(completion.evidence, message_hash=digest(message_json)),
            )

    with pytest.raises(ModelProtocolError, match="MODEL_BINDING_RECEIPT_MISMATCH"):
        await ProtectedModel(
            InconsistentProvider(BailianCredentials(KEY, ENDPOINT)),
            context,
            protected_values=(secret,),
            budget=budget,
        ).complete(MESSAGES, [])
    assert metadata(context, "MODEL_RESPONSE_CHECKED") == []
    assert secret not in json.dumps(context.trace.payloads)
    assert budget.view()["pending_requests"] == 0


@pytest.mark.parametrize(
    "response", [{"content": "\ud800"}, {"content": float("nan")}, ["not a message"]]
)
async def test_invalid_scripted_response_keeps_safe_block_and_settles_budget(response, budget):
    class Invalid:
        async def complete(self, messages, tools):
            return response

    context = gateway()
    with pytest.raises(ModelProtocolError, match="MODEL_CONTEXT_INVALID"):
        await ProtectedModel(Invalid(), context, budget=budget).complete(MESSAGES, [])
    refused = metadata(context, "MODEL_EGRESS_BLOCKED")[-1]
    assert refused["direction"] == "RESPONSE"
    checked = metadata(context, "MODEL_REQUEST_CHECKED")[0]
    assert (
        refused["call_id"] == checked["call_id"]
        and refused["budget_ticket"] == checked["budget_ticket"]
    )
    if isinstance(response, dict):
        assert refused["response_hash"] is None and refused["response_hash_status"] == "UNAVAILABLE"
    assert budget.view()["pending_requests"] == 0 and budget.view()["requests_reserved"] == 1


@pytest.mark.parametrize("broken_body", ["not-json", "empty-choices", "wrong-shape"])
async def test_malformed_local_completion_body_is_safely_closed(broken_body, transport, budget):
    transport()
    context = gateway()

    class BrokenCompletion(BailianChatModel):
        async def complete_prepared(self, prepared):
            completion = await super().complete_prepared(prepared)
            body = {"not-json": KEY, "empty-choices": '{"choices":[]}', "wrong-shape": "[]"}[
                broken_body
            ]
            return replace(completion, body_json=body)

    with pytest.raises(ModelProtocolError, match="MODEL_BACKEND_FAILED") as error:
        await ProtectedModel(
            BrokenCompletion(BailianCredentials(KEY, ENDPOINT)), context, budget=budget
        ).complete(MESSAGES, [])
    refused = metadata(context, "MODEL_EGRESS_BLOCKED")[-1]
    checked = metadata(context, "MODEL_REQUEST_CHECKED")[0]
    assert (
        refused["call_status"] == "FAILED" and refused["budget_ticket"] == checked["budget_ticket"]
    )
    assert metadata(context, "MODEL_RESPONSE_CHECKED") == []
    assert KEY not in str(error.value) + json.dumps(context.trace.payloads)
    assert budget.view()["pending_requests"] == 0
