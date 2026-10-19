"""Finite protocol boundaries and genuine owned-runner failure/cleanup checks."""

import asyncio
import json

import pytest
import run_controlled_model_comparison_v1 as runner
from core_parameterized_tasks import generate, seal_instances
from evaluation_models import IOCCalibrationModel
from model_comparison_protocol import (
    PROFILES,
    SEED,
    load_protocol,
    planned_cells,
    planned_pairs,
    protocol_template,
    validate_protocol,
)
from sujie_demo_agent.bailian_agent import BailianChatModel, BailianCredentials, ModelProtocolError


@pytest.fixture
def inputs(tmp_path):
    directory = tmp_path / "inputs"
    seal_instances(directory, [generate(profile, SEED) for profile in PROFILES])
    return directory


def test_exact_plan_has48_distinct_cells14_pairs_and6_shared_fact_groups():
    protocol = validate_protocol(protocol_template())
    instances = {f"{profile}-seed-{SEED}": generate(profile, SEED) for profile in PROFILES}
    pairs = planned_pairs(protocol, instances)
    cells = planned_cells(pairs)
    assert len(pairs) == 14
    assert len(cells) == len(set(cells)) == 48
    assert len({pair["fact_group_id"] for pair in pairs}) == 6
    for profile in PROFILES:
        assert len({pair["instance_id"] for pair in pairs if pair["profile"] == profile}) == 1
    assert len([pair for pair in pairs if pair["classes"] == ["C", "R"]]) == 1
    assert sum(len(pair["variants"]) for pair in pairs if pair["scenario"] == "quoted") == 6
    assert protocol["experiment_mode"] == "observational"
    assert protocol["formal_ready"] is False
    assert "expected_observations" not in protocol


def test_primary_rotation_and_preselected_ablations_are_deterministic():
    pairs = protocol_template()["pairs"]
    assert [pair["variants"][:3] for pair in pairs if pair["scenario"] == "clean"] == [
        ["unsafe", "strong-static", "full"],
        ["strong-static", "full", "unsafe"],
        ["full", "unsafe", "strong-static"],
        ["unsafe", "strong-static", "full"],
        ["strong-static", "full", "unsafe"],
        ["full", "unsafe", "strong-static"],
    ]
    assert {
        pair["profile"]
        for pair in pairs
        if pair["scenario"] == "injected" and len(pair["variants"]) == 5
    } == {"event-timeline", "delegated-report", "memory-update"}


@pytest.mark.parametrize("raw", ('{"formal_ready":false,"formal_ready":false}', '{"seed":NaN}'))
def test_protocol_bytes_reject_duplicate_fields_and_nonfinite_values(tmp_path, raw):
    path = tmp_path / "protocol.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="COMPARISON_PROTOCOL_(?:DUPLICATE_FIELD|NONFINITE_JSON)"):
        load_protocol(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("formal_ready", 0),
        ("formal_ready", True),
        ("seed", True),
        ("seed", 1),
        ("task_provider_requests", 13),
        ("task_reservation_units", 199999),
        ("cloud_execution_enabled", True),
        ("experiment_mode", "efficacy-pass"),
        ("unknown", "field"),
        ("maximum_global_requests", float("nan")),
    ],
)
def test_protocol_is_strict_and_does_not_accept_control_or_numeric_drift(field, value):
    protocol = protocol_template()
    protocol[field] = value
    with pytest.raises(ValueError):
        validate_protocol(protocol)


@pytest.mark.parametrize(
    "selected", ([], ["unknown"], ["ioc-transfer--clean"] * 2, "ioc-transfer--clean")
)
def test_selection_rejects_unknown_duplicate_empty_or_nonlist_pairs(selected):
    instances = {f"{profile}-seed-{SEED}": generate(profile, SEED) for profile in PROFILES}
    with pytest.raises(ValueError):
        planned_pairs(protocol_template(), instances, selected)


@pytest.mark.parametrize(
    ("requests", "units"), [(True, 1), (0, 1), (37, 1), (1, True), (1, 0), (1, 600001)]
)
def test_budget_ceiling_rejects_bool_zero_or_matrix_overflow(requests, units):
    with pytest.raises(ValueError, match="COMPARISON_GLOBAL_BUDGET_INVALID"):
        runner.budget_limits(protocol_template(), 3, requests, units)


async def test_live_mode_is_rejected_before_inputs_or_any_credential_read(tmp_path):
    out = tmp_path / "never-created"
    with pytest.raises(ValueError, match="COMPARISON_LIVE_PROVIDER_DISABLED"):
        await runner.evaluate(out, instance_dir=tmp_path / "absent", execution_mode="cloud")
    assert not out.exists()


def test_real_shaped_provider_is_rejected_without_active_closed_transport():
    backend = BailianChatModel(
        BailianCredentials("sk-synthetic-no-transport-key", "https://must-not-contact.invalid/v1"),
        model="qwen-plus-2025-12-01",
        max_tokens=1024,
        timeout=30,
    )
    with pytest.raises(ValueError, match="COMPARISON_OFFLINE_MODEL_RECIPE_INVALID"):
        runner._offline_recipe(backend, protocol_template())
    assert backend.transport_attempts == 0


async def test_complete_selected_pair_records_validity_separately_from_outcomes(inputs, tmp_path):
    result = await runner.evaluate(
        tmp_path / "run", instance_dir=inputs, selected_pair_ids=["ioc-transfer--clean"]
    )
    assert result["run_status"] == "FINISHED"
    assert result["records_valid"] and result["passed"]
    assert len(result["cases"]) == 3
    assert len(result["omitted_protocol_pair_ids"]) == 13
    assert result["provider_transport_attempts"] == result["cloud_calls"] == 0
    assert all(row["record_valid"] for row in result["cases"])
    assert all(row["owned_worker_and_contexts_closed"] for row in result["cleanup_observations"])
    assert all(
        request["call_id"]
        and request["budget_ticket"]
        and request["messages_tools_b64"]
        and request["effective_body_b64"] is None
        for row in result["cases"]
        for model in row["models"]
        for request in model["requests"]
    )


class FailingIOC:
    def __init__(self, fail):
        self.fail = fail
        self.backend = IOCCalibrationModel()

    async def complete(self, messages, tools):
        if self.fail:
            raise ModelProtocolError("BAILIAN_TRANSPORT_ERROR")
        return await self.backend.complete(messages, tools)


async def test_ordinary_agent_failure_keeps_observations_and_continues(inputs, tmp_path):
    created = []

    def factory(profile):
        model = FailingIOC(not created)
        created.append(model)
        return model

    result = await runner.evaluate(
        tmp_path / "run",
        instance_dir=inputs,
        selected_pair_ids=["ioc-transfer--clean"],
        backend_factory=factory,
    )
    assert result["records_valid"]
    assert [row["agent"]["status"] for row in result["cases"]] == ["FAILED", "FINISHED", "FINISHED"]
    assert not result["cases"][0]["assessment"]["execution_finished_without_error"]
    assert result["cases"][0]["record_valid"]
    assert not result["failed_cell_attempts"]


async def test_global_budget_exhaustion_retains_first_record_and_unexecuted_cells(inputs, tmp_path):
    result = await runner.evaluate(
        tmp_path / "run",
        instance_dir=inputs,
        selected_pair_ids=["ioc-transfer--clean"],
        total_request_limit=1,
    )
    assert result["run_status"] == "BUDGET_EXHAUSTED"
    assert not result["records_valid"]
    assert len(result["cases"]) == len(result["attempted_cells"]) == 1
    assert len(result["unexecuted_cells"]) == 2
    assert result["service_budget"]["requests_reserved"] == 1
    assert result["service_budget"]["unknown_usage_requests"] == 1


async def test_insufficient_global_units_stops_even_when_positive_units_remain(inputs, tmp_path):
    result = await runner.evaluate(
        tmp_path / "run",
        instance_dir=inputs,
        selected_pair_ids=["ioc-transfer--clean"],
        total_unit_limit=1,
    )
    assert result["run_status"] == "BUDGET_EXHAUSTED"
    assert len(result["attempted_cells"]) == 1
    assert len(result["unexecuted_cells"]) == 2
    assert result["service_budget"]["remaining_units"] == 1
    assert result["provider_transport_attempts"] == 0
    assert result["cases"][0]["agent"]["error_code"] == "MODEL_BUDGET_UNITS_EXHAUSTED"


async def test_cancellation_retains_partial_export_and_unknown_outcome(
    inputs, tmp_path, monkeypatch
):
    async def cancel(*args, **kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(runner, "run_model_session", cancel)
    out = tmp_path / "run"
    with pytest.raises(asyncio.CancelledError):
        await runner.evaluate(out, instance_dir=inputs, selected_pair_ids=["ioc-transfer--clean"])
    summary = json.loads((out / "summary.json").read_bytes())
    assert summary["run_status"] == "CANCELLED"
    assert summary["failed_cell_attempts"][0]["unsafe_effect_observed"] is None
    assert summary["failed_cell_attempts"][0]["partial_export"]
    assert len(summary["unexecuted_cells"]) == 2
    assert summary["cleanup_observations"][0]["owned_worker_and_contexts_closed"]


async def test_cleanup_failure_stops_before_next_cell(inputs, tmp_path, monkeypatch):
    original = runner.bounded_stop

    async def false_cleanup(session):
        await original(session)
        session.cleanup_complete = False
        return False

    monkeypatch.setattr(runner, "bounded_stop", false_cleanup)
    out = tmp_path / "run"
    with pytest.raises(RuntimeError, match="COMPARISON_CLEANUP_NOT_CONFIRMED"):
        await runner.evaluate(out, instance_dir=inputs, selected_pair_ids=["ioc-transfer--clean"])
    summary = json.loads((out / "summary.json").read_bytes())
    assert summary["run_status"] == "FAILED"
    assert len(summary["cases"]) == len(summary["attempted_cells"]) == 1
    assert not summary["cleanup_observations"][0]["owned_worker_and_contexts_closed"]


async def test_cancellation_after_last_cell_keeps_complete_but_unregistered_pair(
    inputs, tmp_path, monkeypatch
):
    original, closed = runner.bounded_stop, []

    async def late_cancel(session):
        result = await original(session)
        closed.append(session.id)
        return len(closed) == 3 or result

    monkeypatch.setattr(runner, "bounded_stop", late_cancel)
    out = tmp_path / "run"
    with pytest.raises(asyncio.CancelledError):
        await runner.evaluate(out, instance_dir=inputs, selected_pair_ids=["ioc-transfer--clean"])
    summary = json.loads((out / "summary.json").read_bytes())
    assert summary["run_status"] == "CANCELLED"
    assert len(summary["cases"]) == 3 and not summary["paired_checks"]
    assert not summary["passed"]


async def test_integrity_exception_stops_with_unknown_partial_instead_of_continuing(
    inputs, tmp_path, monkeypatch
):
    def corrupt(*args):
        raise ValueError("SYNTHETIC_INTEGRITY_FAILURE")

    monkeypatch.setattr(runner, "observe", corrupt)
    out = tmp_path / "run"
    with pytest.raises(ValueError, match="SYNTHETIC_INTEGRITY_FAILURE"):
        await runner.evaluate(out, instance_dir=inputs, selected_pair_ids=["ioc-transfer--clean"])
    summary = json.loads((out / "summary.json").read_bytes())
    assert summary["run_status"] == "FAILED"
    assert not summary["cases"]
    assert len(summary["failed_cell_attempts"]) == 1
    assert len(summary["unexecuted_cells"]) == 2
