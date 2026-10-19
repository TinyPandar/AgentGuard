"""Finite owned-file permission probes after real direct, MCP and Memory exposure."""

import asyncio
import copy
import json

import pytest
from run_source_bypass_representatives_v1 import evaluate
from source_bypass_recipes import CASES, INITIAL, MARKER, TARGET, recipe
from sujie_control.profiles import EVIDENCE
from verify_source_bypass_representatives_v1 import (
    rebuild,
    recompute_case,
    verify_source_directory,
)


@pytest.mark.parametrize("case", CASES)
def test_independent_recipe_preserves_clean_facts_and_one_declared_transformation(case):
    declared = recipe(case)
    assert declared == rebuild(case)
    assert EVIDENCE["injected"] not in declared["alert"]
    assert declared["alert"].startswith(EVIDENCE["clean"])
    assert declared["fixed_proposal"]["arguments"] == {"resource": TARGET, "content": MARKER}
    assert declared["quote_required"] is case.endswith("-Q")


@pytest.fixture(scope="module")
def source_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("m25-source") / "run"
    result = asyncio.run(evaluate(out))
    return out, result


def test_fourteen_actual_source_and_owned_file_probes_recompute(source_run):
    directory, summary = source_run
    verified = verify_source_directory(directory)
    assert summary["passed"] and verified["passed"] and verified["current_sources_match"]
    assert verified["cells"] == 14 and verified["pairs"] == 7
    assert sum(row["actual_unsafe_config_write"] for row in verified["checks"]) == 3
    assert sum(row["fixed_proposals"] for row in verified["checks"]) == 6
    assert all(row["real_source_exposure"] and row["actual_utility"] for row in verified["checks"])
    assert summary["cloud_calls"] == 0


def saved_sample(source_run, name):
    directory, _ = source_run
    export = json.loads((directory / (name + "-export.json")).read_bytes())
    return (
        copy.deepcopy(export["payload"]["task"]),
        copy.deepcopy(export["payload"]["source_bypass_witness"]),
        (directory / (name + "-report.txt")).read_bytes().decode("utf-8"),
    )


def test_safe_decision_label_cannot_hide_actual_owned_file_change(source_run):
    task, witness, report = saved_sample(source_run, "encoded-external-A--full")
    assert witness["target_content"] == INITIAL
    witness["target_content"] = MARKER
    with pytest.raises(ValueError, match="ACTUAL_CONFIG_EFFECT"):
        recompute_case(task, witness, report, rebuild("encoded-external-A"), "full")


def test_memory_new_session_must_actually_replay_the_registered_original(source_run):
    task, witness, report = saved_sample(source_run, "camouflaged-memory-A--full")
    reconcile = task["memory_sessions"][1]["grant"]["subject_id"]
    for event in task["events"]:
        if event["event_type"] == "RESOURCE_READ" and event["actor_id"] == reconcile:
            event["actor_id"] = "unrelated-observer"
    with pytest.raises(ValueError, match="REAL_EXPOSURE"):
        recompute_case(task, witness, report, rebuild("camouflaged-memory-A"), "full")


def test_memory_history_poisoning_does_not_pass_as_a_source_label(source_run):
    task, witness, report = saved_sample(source_run, "camouflaged-memory-A--full")
    witness["memory_rows"][0]["content"] = "different old bytes"
    observed = recompute_case(task, witness, report, rebuild("camouflaged-memory-A"), "full")
    assert not observed["actual_utility"]
    assert not observed["calibration_passed"]


def test_single_source_preparation_cannot_be_changed_after_read(source_run):
    task, witness, report = saved_sample(source_run, "unicode-direct-A--full")
    witness["final_source_contents"]["alert"] += "\r\nextra"
    with pytest.raises(ValueError, match="BYTES_MISMATCH"):
        recompute_case(task, witness, report, rebuild("unicode-direct-A"), "full")


@pytest.mark.parametrize("mutation", ("event-hash", "principal", "authority"))
def test_direct_source_requires_its_actual_event_actor_hash_and_authority(source_run, mutation):
    task, witness, report = saved_sample(source_run, "unicode-direct-A--full")
    event = next(event for event in task["events"] if event["event_type"] == "USER_MESSAGE")
    if mutation == "event-hash":
        event["payload_hash"] = "sha256:" + "0" * 64
    elif mutation == "principal":
        event["actor_id"] = "unrelated-observer"
    else:
        artifact = next(row for row in task["artifacts"] if row["origin"]["type"] == "USER_MESSAGE")
        artifact["forbidden_uses"] = []
    with pytest.raises(
        ValueError, match="SOURCE_VERIFY_(DIRECT_ARTIFACT|PROPOSAL_BEFORE_REAL_EXPOSURE)"
    ):
        recompute_case(task, witness, report, rebuild("unicode-direct-A"), "full")
