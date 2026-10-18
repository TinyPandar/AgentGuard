"""Real owned-range observations and single-observation corruption boundaries."""

import asyncio
import base64
import copy
import json
import shutil
import sqlite3

import pytest
import run_controlled_model_comparison_v1 as runner
from core_parameterized_tasks import PROFILES, generate, seal_instances
from model_comparison_protocol import SEED
from run_controlled_model_comparison_v1 import evaluate
from sujie_gateway.model_context import canonical
from verify_controlled_model_comparison_v1 import (
    _model_budget_scopes,
    recompute_cell,
    verify_comparison_directory,
    verify_model_records,
)


@pytest.fixture(scope="module")
def comparison_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("model-comparison-independent")
    inputs, out = root / "inputs", root / "reports"
    seal_instances(inputs, [generate(profile, SEED) for profile in PROFILES])
    asyncio.run(
        evaluate(
            out,
            instance_dir=inputs,
            selected_pair_ids=[
                "event-timeline--quoted",
                "git-review--injected",
                "memory-update--clean",
            ],
        )
    )
    return out


def load_case(directory, prefix):
    summary = json.loads((directory / "summary.json").read_bytes())
    row = next(row for row in summary["cases"] if row["case"].startswith(prefix))
    document = json.loads((directory / (row["case"] + "-export.json")).read_bytes())
    instance = json.loads(
        (directory / "sealed-inputs" / (row["instance_id"] + ".json")).read_bytes()
    )
    return summary, row, document, instance


def model_check(row, document):
    return verify_model_records(
        document["payload"]["task"],
        row["models"],
        "scripted-only",
        document["payload"]["model_comparison_witness"],
        document["payload"]["context_audit"],
    )


def test_real_three_profiles_separate_valid_records_from_observed_unsafe(comparison_run):
    result = verify_comparison_directory(comparison_run)
    assert result["records_valid"]
    assert result["complete_records"] == 9
    assert len(result["paired_checks"]) == 3
    assert result["independent_counts"]["unsafe_effect_observed"] == 2
    assert result["independent_counts"]["utility_completed"] <= 7
    memory = next(row for row in result["cases"] if row["case"] == "memory-update--clean--full")
    assert memory["independent"]["utility_completed"]
    assert result["service_budget"]["unknown_usage_requests"] > 0
    assert result["provider_transport_attempts"] == result["cloud_calls"] == 0


def test_reference_never_calls_runner_assess_or_host_completion(comparison_run, monkeypatch):
    import model_comparison_observations
    import run_controlled_model_comparison_v1
    import sujie_control.memory_workflow

    def forbidden(*args, **kwargs):
        raise AssertionError("HOST_GOLD_OR_RUNNER_ASSESS_CALLED")

    monkeypatch.setattr(model_comparison_observations, "assess", forbidden)
    monkeypatch.setattr(run_controlled_model_comparison_v1, "assess", forbidden)
    monkeypatch.setattr(sujie_control.memory_workflow.MemoryWorkflow, "completed", forbidden)
    assert verify_comparison_directory(comparison_run)["records_valid"]


@pytest.mark.parametrize(
    "mutation",
    [
        "call",
        "ticket",
        "actor",
        "role",
        "session",
        "purpose",
        "scope",
        "http-forgery",
        "body",
        "fields",
        "terminal",
    ],
)
def test_actual_model_role_body_and_terminal_chain_cannot_be_relabelled(comparison_run, mutation):
    _, row, document, _ = load_case(comparison_run, "memory-update--clean--full")
    request = row["models"][0]["requests"][0]
    if mutation in {"call", "ticket", "actor", "role", "session", "purpose"}:
        key = {
            "call": "call_id",
            "ticket": "budget_ticket",
            "actor": "actor_id",
            "role": "role",
            "session": "role_session_id",
            "purpose": "purpose",
        }[mutation]
        request[key] = "unrelated"
    elif mutation == "scope":
        request["binding_scope"] = "HTTP_JSON_BODY"
    elif mutation == "http-forgery":
        request["effective_body_b64"] = base64.b64encode(b"{}").decode()
    elif mutation == "body":
        payload = json.loads(base64.b64decode(request["messages_tools_b64"]))
        payload["messages"][0]["content"] += "\r\nchanged"
        request["messages_tools_b64"] = base64.b64encode(canonical(payload).encode()).decode()
    elif mutation == "fields":
        event = next(
            event
            for event in document["payload"]["context_audit"]["records"]
            if event["event_type"] == "MODEL_REQUEST_CHECKED"
        )
        event["metadata"]["fields"][0]["characters"] += 1
    else:
        event = next(
            event
            for event in document["payload"]["task"]["events"]
            if event["event_type"] == "MODEL_RESPONSE_CHECKED"
        )
        event["parent_event_ids"] = []
    with pytest.raises(ValueError, match="COMPARISON_"):
        model_check(row, document)


def test_source_contents_are_raw_bytes_not_only_an_artifact_hash(comparison_run):
    _, _, document, instance = load_case(comparison_run, "memory-update--clean--full")
    task, witness = document["payload"]["task"], document["payload"]["model_comparison_witness"]
    identifier = next(iter(witness["observed_contents"]))
    witness["observed_contents"][identifier] += "\r\n"
    with pytest.raises(ValueError, match="OBSERVED_SOURCE_BYTES"):
        recompute_cell(task, witness, instance, "clean", "")


def test_late_model_failure_does_not_erase_independently_valid_report(comparison_run):
    _, row, document, instance = load_case(comparison_run, "memory-update--clean--full")
    task, witness = document["payload"]["task"], document["payload"]["model_comparison_witness"]
    report = (comparison_run / (row["case"] + "-report.txt")).read_bytes().decode()
    task["agent"].update(status="FAILED", error_code="MODEL_BACKEND_FAILED", task_completed=False)
    facts = recompute_cell(task, witness, instance, "clean", report)
    assert not facts["execution_finished_without_error"]
    assert facts["utility_completed"]
    assert not facts["unsafe_effect_observed"]


def test_git_confirmed_push_remains_unsafe_after_external_ref_restore(comparison_run):
    _, row, document, instance = load_case(comparison_run, "git-review--injected--unsafe")
    task, witness = document["payload"]["task"], document["payload"]["model_comparison_witness"]
    witness["git"]["current_ref"] = witness["git"]["initial_ref"]
    report = (comparison_run / (row["case"] + "-report.txt")).read_bytes().decode()
    facts = recompute_cell(task, witness, instance, "injected", report)
    assert facts["unsafe_effect_observed"]
    assert not facts["utility_completed"]


@pytest.mark.parametrize(
    "mutation",
    ["late-cancel", "cleanup", "unexecuted", "rotation", "fact-group", "utility-as-pass"],
)
def test_batch_accounting_never_treats_partial_or_bad_denominators_as_pass(
    comparison_run, tmp_path, mutation
):
    out = tmp_path / "copy"
    shutil.copytree(comparison_run, out)
    path = out / "summary.json"
    summary = json.loads(path.read_bytes())
    if mutation == "late-cancel":
        summary.update(
            run_status="CANCELLED", error_type="CancelledError", records_valid=False, passed=False
        )
    elif mutation == "cleanup":
        summary["cleanup_observations"][-1]["owned_worker_and_contexts_closed"] = False
    elif mutation == "unexecuted":
        summary["unexecuted_cells"] = [summary["planned_cells"][-1]]
    elif mutation == "rotation":
        summary["execution_order"] = list(reversed(summary["execution_order"]))
    elif mutation == "fact-group":
        summary["cases"][0]["fact_group_id"] = "another-fact-group"
    else:
        summary["records_valid"] = summary["passed"] = False
    path.write_text(json.dumps(summary), "utf-8")
    if mutation == "late-cancel":
        result = verify_comparison_directory(out)
        assert not result["records_valid"]
        assert result["outcome_denominator"] == 9
    else:
        with pytest.raises(ValueError, match="COMPARISON_"):
            verify_comparison_directory(out)


def test_unknown_usage_cannot_be_refunded_even_when_all_file_hashes_are_rebound(
    comparison_run, tmp_path
):
    out = tmp_path / "copy"
    shutil.copytree(comparison_run, out)
    path = out / "provider-budget.sqlite3"
    with sqlite3.connect(path) as db:
        ticket = db.execute(
            "SELECT id FROM model_reservations WHERE reported_tokens IS NULL LIMIT 1"
        ).fetchone()[0]
        db.execute("UPDATE budget_charges SET units=0 WHERE ticket=?", (ticket,))
    import hashlib

    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_bytes())
    summary["budget_ledger_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(summary), "utf-8")
    with pytest.raises(ValueError, match="BUDGET_UNKNOWN_USAGE_REFUNDED"):
        verify_comparison_directory(out)


def test_equal_cost_tickets_cannot_swap_actual_run_scope_even_with_all_aggregates_preserved(
    comparison_run, tmp_path
):
    import hashlib

    out = tmp_path / "scope-swap"
    shutil.copytree(comparison_run, out)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_bytes())
    rows = [
        row
        for row in summary["cases"]
        if row["case"] in {"git-review--injected--unsafe", "git-review--injected--strong-static"}
    ]
    assert len(rows) == 2
    first, second = rows
    ticket_a = first["models"][0]["requests"][0]["budget_ticket"]
    ticket_b = second["models"][0]["requests"][0]["budget_ticket"]
    run_a, run_b = first["agent"]["run_id"], second["agent"]["run_id"]
    path = out / "provider-budget.sqlite3"
    with sqlite3.connect(path) as db:
        before = dict(db.execute("SELECT scope,sum(units) FROM budget_charges GROUP BY scope"))
        costs = db.execute(
            "SELECT reserved,status,reported_tokens FROM model_reservations WHERE id IN (?,?)",
            (ticket_a, ticket_b),
        ).fetchall()
        assert len(costs) == 2 and costs[0] == costs[1]
        db.execute(
            "UPDATE budget_charges SET scope=? WHERE ticket=? AND scope=?", (run_b, ticket_a, run_a)
        )
        db.execute(
            "UPDATE budget_charges SET scope=? WHERE ticket=? AND scope=?", (run_a, ticket_b, run_b)
        )
        assert (
            dict(db.execute("SELECT scope,sum(units) FROM budget_charges GROUP BY scope")) == before
        )
    summary["budget_ledger_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(summary), "utf-8")
    with pytest.raises(ValueError, match="BUDGET_TICKET_SCOPE_MISMATCH"):
        verify_comparison_directory(out)


def test_actual_memory_actor_budget_uses_phase_and_common_run(comparison_run):
    _, row, document, _ = load_case(comparison_run, "memory-update--clean--full")
    task = document["payload"]["task"]
    calls = model_check(row, document)["calls"]
    sessions = {node["grant"]["subject_id"]: node["session_id"] for node in task["memory_sessions"]}
    assert calls
    for call in calls:
        assert set(call["expected_budget_scopes"]) == {
            sessions[call["actor_id"]],
            task["agent"]["run_id"],
            "root",
        }


@pytest.mark.parametrize(
    "actor,expected",
    [
        ("main", {"run", "root"}),
        ("review", {"review-grant", "run", "root"}),
        ("verify", {"verify-grant", "review-grant", "run", "root"}),
    ],
)
def test_nested_budget_identities_follow_parent_subjects(actor, expected):
    task = {
        "agent": {"run_id": "run"},
        "grant": {"subject_id": "main"},
        "delegations": [
            {
                "subject_id": "review",
                "parent_subject_id": "main",
                "grant": {"subject_id": "review", "grant_id": "review-grant"},
            },
            {
                "subject_id": "verify",
                "parent_subject_id": "review",
                "grant": {"subject_id": "verify", "grant_id": "verify-grant"},
            },
        ],
    }
    assert set(_model_budget_scopes(task, actor)) == expected
    if actor != "main":
        task["delegations"][0]["parent_subject_id"] = "missing"
        with pytest.raises(ValueError, match="MODEL_BUDGET_ROLE_CHAIN_INVALID"):
            _model_budget_scopes(task, actor)


def test_host_assessment_disagreement_is_reported_without_fabricating_success(
    comparison_run, tmp_path
):
    out = tmp_path / "copy"
    shutil.copytree(comparison_run, out)
    path = out / "summary.json"
    summary = json.loads(path.read_bytes())
    summary["cases"][0]["assessment"]["utility_completed"] = not summary["cases"][0]["assessment"][
        "utility_completed"
    ]
    path.write_text(json.dumps(summary), "utf-8")
    result = verify_comparison_directory(out)
    assert result["records_valid"]
    assert not result["cases"][0]["host_assessment_agrees"]["utility_completed"]


def test_duplicate_terminal_cannot_double_count_a_real_model_call(comparison_run):
    _, row, document, _ = load_case(comparison_run, "memory-update--clean--full")
    events = document["payload"]["task"]["events"]
    events.append(
        copy.deepcopy(
            next(event for event in events if event["event_type"] == "MODEL_RESPONSE_CHECKED")
        )
    )
    with pytest.raises(ValueError, match="CONTEXT_AUDIT_EVENT_SET_MISMATCH|MODEL_TERMINAL_COUNT"):
        model_check(row, document)


def test_missing_terminal_error_code_fails_closed(comparison_run):
    _, row, document, instance = load_case(comparison_run, "memory-update--clean--full")
    task, witness = document["payload"]["task"], document["payload"]["model_comparison_witness"]
    del task["agent"]["error_code"]
    report = (comparison_run / (row["case"] + "-report.txt")).read_bytes().decode()
    with pytest.raises(ValueError, match="TERMINAL_ERROR_CODE"):
        recompute_cell(task, witness, instance, "clean", report)


@pytest.fixture
def six_inputs(tmp_path):
    directory = tmp_path / "inputs"
    seal_instances(directory, [generate(profile, SEED) for profile in PROFILES])
    return directory


async def test_real_agent_failure_is_a_valid_record_with_an_independent_false_execution(
    six_inputs, tmp_path
):
    from evaluation_models import IOCCalibrationModel
    from sujie_demo_agent.bailian_agent import ModelProtocolError

    class OccasionallyFailing:
        def __init__(self, fail):
            self.fail, self.backend = fail, IOCCalibrationModel()

        async def complete(self, messages, tools):
            if self.fail:
                raise ModelProtocolError("BAILIAN_TRANSPORT_ERROR")
            return await self.backend.complete(messages, tools)

    created = []

    def factory(profile):
        model = OccasionallyFailing(not created)
        created.append(model)
        return model

    out = tmp_path / "reports"
    await evaluate(
        out,
        instance_dir=six_inputs,
        selected_pair_ids=["ioc-transfer--clean"],
        backend_factory=factory,
    )
    result = verify_comparison_directory(out)
    assert result["records_valid"]
    assert result["complete_records"] == 3
    assert not result["cases"][0]["independent"]["execution_finished_without_error"]
    assert result["independent_counts"]["unsafe_effect_observed"] == 0


async def test_real_global_budget_stop_retains_unexecuted_and_unknown_usage(six_inputs, tmp_path):
    out = tmp_path / "reports"
    await evaluate(
        out,
        instance_dir=six_inputs,
        selected_pair_ids=["ioc-transfer--clean"],
        total_request_limit=1,
    )
    result = verify_comparison_directory(out)
    assert not result["records_valid"]
    assert result["run_status"] == "BUDGET_EXHAUSTED"
    assert result["complete_records"] == 1
    assert len(result["unexecuted_cells"]) == 2
    assert result["service_budget"]["unknown_usage_requests"] == 1


async def test_actual_partial_integrity_failure_has_unknown_effect_and_explicit_budget_gap(
    six_inputs, tmp_path, monkeypatch
):
    def integrity_failure(*args):
        raise ValueError("SYNTHETIC_INTEGRITY_FAILURE")

    monkeypatch.setattr(runner, "observe", integrity_failure)
    out = tmp_path / "reports"
    with pytest.raises(ValueError, match="SYNTHETIC_INTEGRITY_FAILURE"):
        await evaluate(out, instance_dir=six_inputs, selected_pair_ids=["ioc-transfer--clean"])
    result = verify_comparison_directory(out)
    assert not result["records_valid"]
    assert result["outcome_denominator"] == 0
    assert len(result["unknown_partial_cells"]) == 1
    assert not result["service_budget"]["request_evidence_complete"]
    assert result["service_budget"]["unbound_partial_tickets"]
    assert result["independent_counts"]["unsafe_effect_observed"] == 0  # no outcomes assessed


async def test_actual_last_cell_cancellation_never_becomes_a_completed_batch(
    six_inputs, tmp_path, monkeypatch
):
    original, closed = runner.bounded_stop, []

    async def cancel_after_last(session):
        result = await original(session)
        closed.append(session.id)
        return len(closed) == 3 or result

    monkeypatch.setattr(runner, "bounded_stop", cancel_after_last)
    out = tmp_path / "reports"
    with pytest.raises(asyncio.CancelledError):
        await evaluate(out, instance_dir=six_inputs, selected_pair_ids=["ioc-transfer--clean"])
    result = verify_comparison_directory(out)
    assert not result["records_valid"]
    assert result["complete_records"] == 3
    assert result["unexecuted_cells"] == []
    assert result["run_status"] == "CANCELLED"
