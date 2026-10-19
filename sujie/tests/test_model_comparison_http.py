"""Actual Provider HTTP parsing in a closed transport, with main and long-chain roles."""

import base64
import json

import pytest
from core_parameterized_tasks import generate, seal_instances
from model_comparison_protocol import PROFILES, SEED, protocol_template
from offline_model_comparison_http import OfflineHTTPFactory, closed_transport_admitted
from run_controlled_model_comparison_v1 import evaluate
from sujie_demo_agent.bailian_agent import BailianChatModel, BailianCredentials
from sujie_gateway.model_context import digest
from verify_controlled_model_comparison_v1 import verify_comparison_directory


def inputs(tmp_path):
    path = tmp_path / "inputs"
    seal_instances(path, [generate(profile, SEED) for profile in PROFILES])
    return path


def factory_config():
    recipe = protocol_template()["model_recipe"]
    return {key: recipe[key] for key in ("model", "max_tokens", "temperature", "tool_choice")} | {
        "timeout": recipe["request_timeout_seconds"]
    }


async def test_closed_http_nine_cells_recompute_main_nested_and_memory_bytes(tmp_path):
    out = tmp_path / "http-roles"
    with OfflineHTTPFactory(**factory_config()) as factory:
        result = await evaluate(
            out,
            instance_dir=inputs(tmp_path),
            execution_mode="offline-http",
            backend_factory=factory.make,
            selected_pair_ids=[
                "event-timeline--clean",
                "delegated-report--clean",
                "memory-update--clean",
            ],
        )
    independent = verify_comparison_directory(out)
    assert result["records_valid"] and independent["records_valid"]
    assert len(result["cases"]) == 9 and len(result["paired_checks"]) == 3
    requests = [
        request
        for row in result["cases"]
        for model in row["models"]
        for request in model["requests"]
    ]
    assert len(requests) == len(factory.captures) == result["provider_transport_attempts"]
    assert {row["role"] for row in requests} == {"MAIN", "review", "verify", "capture", "reconcile"}
    assert {row["purpose"] for row in requests} == {"MAIN", "SUBAGENT"}
    nodes = [node for row in result["cases"] for node in row["models"]]
    for ordinal, node in enumerate(nodes):
        captured_calls = [row for row in factory.captures if row["backend_ordinal"] == ordinal]
        assert len(captured_calls) == len(node["requests"])
        for request, captured in zip(node["requests"], captured_calls, strict=True):
            raw = base64.b64decode(request["effective_body_b64"], validate=True).decode("utf-8")
            assert raw == captured["request_body_utf8"]
            assert digest(raw) == request["effective_request_hash"]
            assert json.loads(raw)["max_tokens"] == 1024
            receipt = request["provider_receipt"]
            assert receipt["sent_request_hash"] == digest(raw)
            assert receipt["raw_response_hash"] == captured["response_sha256"]
            assert receipt["call_id"] == request["call_id"]
            assert receipt["budget_ticket"] == request["budget_ticket"]
            assert request["actor_id"] and request["role_session_id"]
    assert result["service_budget"]["requests_reserved"] == len(factory.captures)
    assert result["service_budget"]["reported_tokens"] == 3 * len(factory.captures)
    assert result["service_budget"]["unknown_usage_requests"] == 0
    assert result["cloud_calls"] == 0
    assert "Bearer " not in json.dumps(factory.captures)


async def test_unknown_transport_failure_is_retained_and_next_cell_runs(tmp_path):
    out = tmp_path / "http-failure"
    with OfflineHTTPFactory(faults={1: "transport-error"}, **factory_config()) as factory:
        result = await evaluate(
            out,
            instance_dir=inputs(tmp_path),
            execution_mode="offline-http",
            backend_factory=factory.make,
            selected_pair_ids=["event-timeline--clean"],
        )
    independent = verify_comparison_directory(out)
    assert result["records_valid"] and independent["records_valid"]
    assert len(result["cases"]) == 3
    assert result["cases"][0]["agent"]["status"] == "FAILED"
    assert result["cases"][1]["agent"]["status"] == "FINISHED"
    assert result["cases"][2]["agent"]["status"] == "FINISHED"
    assert result["service_budget"]["unknown_usage_requests"] == 1
    assert result["service_budget"]["charged_units"] > 0
    assert factory.captures[0]["response_sha256"] is None
    assert result["provider_transport_attempts"] == len(factory.captures)


def test_offline_admission_requires_active_owned_closed_transport():
    live_shaped = BailianChatModel(BailianCredentials("synthetic-unused", "https://live.invalid"))
    assert not closed_transport_admitted(live_shaped)
    factory = OfflineHTTPFactory(**factory_config())
    with factory:
        backend = factory.make("ioc-transfer")
        assert closed_transport_admitted(backend)
        assert not closed_transport_admitted(live_shaped)
        with pytest.raises(ValueError, match="CONTEXT_ALREADY_ENTERED"):
            with OfflineHTTPFactory():
                pass
    assert not closed_transport_admitted(backend)


@pytest.mark.parametrize("faults", ({0: "transport-error"}, {True: "http-error"}, {1: "unknown"}))
def test_fault_schedule_does_not_silently_accept_ambiguous_indices(faults):
    with pytest.raises(ValueError, match="FAULT_INVALID"):
        OfflineHTTPFactory(faults=faults)
