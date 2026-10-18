"""Closed MockTransport through the actual Provider parser, never a model experiment."""

import json
from contextlib import contextmanager
from unittest.mock import patch

import httpx
from delegated_instance_model import DelegatedInstanceModel
from evaluation_models import calibration_backend
from sujie_demo_agent.bailian_agent import BailianChatModel, BailianCredentials
from sujie_gateway.model_context import canonical, contains_protected, digest

ENDPOINT = "https://offline-m25.invalid/compatible-mode/v1"
FAULTS = {"transport-error", "missing-usage", "malformed-body", "http-error"}
_ACTIVE = []


class OfflineHTTPFactory:
    """Use only inside an isolated evaluation process; the patch is scoped and restored."""

    def __init__(self, *, faults=None, **model_config):
        self.faults = dict(faults or {})
        if any(
            type(index) is not int or index < 1 or fault not in FAULTS
            for index, fault in self.faults.items()
        ):
            raise ValueError("OFFLINE_HTTP_FAULT_INVALID")
        self.model_config = model_config
        self.captures = []
        self.backends = []
        self._scripts = {}
        self._patch = None

    def __enter__(self):
        if self._patch is not None or _ACTIVE:
            raise ValueError("OFFLINE_HTTP_CONTEXT_ALREADY_ENTERED")
        original_client = httpx.AsyncClient

        def client(*args, **kwargs):
            if "transport" in kwargs:
                raise ValueError("OFFLINE_HTTP_TRANSPORT_OVERRIDE")
            return original_client(*args, transport=httpx.MockTransport(self._respond), **kwargs)

        self._patch = patch("sujie_demo_agent.bailian_agent.httpx.AsyncClient", client)
        self._client_factory = client
        self._patch.start()
        _ACTIVE.append(self)
        return self

    def __exit__(self, *args):
        self._patch.stop()
        self._patch = None
        _ACTIVE.remove(self)

    def make(self, profile):
        if self._patch is None:
            raise ValueError("OFFLINE_HTTP_CONTEXT_REQUIRED")
        key = f"sk-synthetic-m25-offline-provider-{len(self.backends):06d}-not-real"
        script = (
            DelegatedInstanceModel()
            if profile == "delegated-report"
            else calibration_backend(profile)
        )
        backend = BailianChatModel(BailianCredentials(key, ENDPOINT), **self.model_config)
        self._scripts[key] = (profile, script, len(self.backends))
        self.backends.append(backend)
        return backend

    async def _respond(self, request):
        if str(request.url) != ENDPOINT + "/chat/completions" or request.method != "POST":
            raise ValueError("OFFLINE_HTTP_ENDPOINT_MISMATCH")
        authorization = request.headers.get("authorization", "")
        key = authorization.removeprefix("Bearer ")
        if key not in self._scripts or not authorization.startswith("Bearer "):
            raise ValueError("OFFLINE_HTTP_PROVIDER_UNKNOWN")
        profile, script, ordinal = self._scripts[key]
        raw = request.content.decode("utf-8")
        body = json.loads(raw)
        if contains_protected(body, self._scripts):
            raise ValueError("OFFLINE_HTTP_CREDENTIAL_IN_BODY")
        record = {
            "ordinal": len(self.captures) + 1,
            "backend_ordinal": ordinal,
            "profile": profile,
            "request_body_utf8": raw,
            "request_sha256": digest(raw),
            "response_body_utf8": None,
            "response_sha256": None,
            "http_status": None,
            "scope": "actual prepared Provider body captured by in-process MockTransport; no network or model inference",
        }
        self.captures.append(record)
        fault = self.faults.get(record["ordinal"])
        if fault == "transport-error":
            record["termination"] = "TRANSPORT_ERROR"
            raise httpx.ReadTimeout("synthetic closed transport failure", request=request)
        if fault == "malformed-body":
            status, response = 200, "{invalid synthetic JSON"
        elif fault == "http-error":
            status, response = 503, canonical({"error": "synthetic unavailable"})
        else:
            message = await script.complete(body["messages"], body.get("tools", []))
            answer = {"choices": [{"message": message}]}
            if fault != "missing-usage":
                answer["usage"] = {"total_tokens": 3}
            status, response = 200, canonical(answer)
        record.update(
            response_body_utf8=response,
            response_sha256=digest(response),
            http_status=status,
            termination="RETURNED",
        )
        return httpx.Response(
            status, content=response.encode("utf-8"), headers={"Content-Type": "application/json"}
        )


@contextmanager
def offline_factory(recipe):
    if set(recipe) != {
        "model",
        "max_tokens",
        "temperature",
        "tool_choice",
        "request_timeout_seconds",
        "endpoint_scope",
    }:
        raise ValueError("OFFLINE_HTTP_RECIPE_INVALID")
    with OfflineHTTPFactory(
        model=recipe["model"],
        max_tokens=recipe["max_tokens"],
        temperature=recipe["temperature"],
        tool_choice=recipe["tool_choice"],
        timeout=recipe["request_timeout_seconds"],
    ) as factory:
        yield factory.make


def closed_transport_admitted(backend):
    """Refuse accidental live Provider factories mislabeled as offline HTTP."""
    return any(
        factory._patch is not None
        and httpx.AsyncClient is factory._client_factory
        and any(candidate is backend for candidate in factory.backends)
        and backend._credentials.base_url == ENDPOINT
        for factory in _ACTIVE
    )
