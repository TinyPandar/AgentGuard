"""Direct proposals retain physical effects without pretending an Agent ran."""

import copy
import json
import os
import subprocess
import sys

import pytest
import run_common_runtime_validation
from sujie_gateway.m1_runtime import new_id
from variant_calibration import calibrate
from verify_effect_calibration_m23 import PROTOCOL, effect_and_utility, verify_effect_directory
from verify_operator_export import verify


def test_receiver_effect_is_not_equivalent_to_allow_or_business_completion():
    witness = {
        "received_sha256": ["unrequested", "ioc"],
        "original_sha256": "unrequested",
        "permitted_sha256": "ioc",
    }
    task = {
        "oracle": {
            "receiver_requests": 2,
            "ioc_payloads_valid": False,
            "ioc_sent_exactly_once": False,
        },
        "agent": {"task_completed": True},
    }
    assert effect_and_utility("source-transfer", witness, task) == (True, False)
    witness["received_sha256"] = ["ioc"]
    task["oracle"]["receiver_requests"] = 1
    task["oracle"].update(ioc_payloads_valid=True, ioc_sent_exactly_once=True)
    task["agent"]["task_completed"] = False
    assert effect_and_utility("source-transfer", witness, task) == (False, True)
    task["oracle"]["receiver_requests"] = 0
    with pytest.raises(ValueError, match="EFFECT_RECEIVER_COUNT_MISMATCH"):
        effect_and_utility("source-transfer", witness, task)


def test_authorized_git_utility_requires_an_actual_changed_ref_and_push_receipt():
    witness = {
        "observed_commit": "old",
        "initial_commit": "old",
        "candidate_commit": "new",
        "actual_push_attempts": 1,
    }
    task = {
        "oracle": {
            "git_remote_commit": "old",
            "git_initial": "old",
            "git_candidate": "new",
            "git_push_attempts": 1,
            "git_push_confirmed": 0,
        }
    }
    assert effect_and_utility("authorized-push", witness, task) == (False, False)
    witness["observed_commit"] = "new"
    task["oracle"].update(git_remote_commit="new", git_push_confirmed=1)
    assert effect_and_utility("authorized-push", witness, task) == (False, True)
    assert effect_and_utility("readonly-push", witness, task) == (True, False)
    witness["actual_push_attempts"] = 0
    task["oracle"]["git_push_attempts"] = 0
    with pytest.raises(ValueError, match="EFFECT_GIT_RECEIPT_MISMATCH"):
        effect_and_utility("authorized-push", witness, task)


@pytest.mark.parametrize("case", ["authorized-push", "source-transfer", "exec-floor"])
async def test_separate_effect_observations_must_not_contradict_each_other(case):
    row = await calibrate("full", case, new_id())
    task = copy.deepcopy(row["task"])
    if case == "authorized-push":
        task["oracle"]["git_remote_commit"] = "contradictory-old-ref"
        expected = "EFFECT_GIT_ORACLE_MISMATCH"
    elif case == "source-transfer":
        task["oracle"]["ioc_payloads_valid"] = False
        expected = "EFFECT_IOC_ORACLE_MISMATCH"
    else:
        task["oracle"]["process_starts"] += 1
        expected = "EFFECT_PROCESS_ORACLE_MISMATCH"
    with pytest.raises(ValueError, match=expected):
        effect_and_utility(case, row["effect_witness"], task)


@pytest.mark.parametrize("case", ["exec-floor", "network-scope"])
async def test_actual_written_report_is_observed_and_independently_checked(case):
    row = await calibrate("full", case, new_id())
    task = row["task"]
    assert task["agent"]["status"] == "NOT_STARTED"
    assert verify(row["export"])["ok"]
    witness = row["effect_witness"]
    assert effect_and_utility(case, witness, task) == (False, True)
    corrupted = copy.deepcopy(witness)
    if case == "exec-floor":
        report = json.loads(corrupted["report_content"])
        report["actual_sha256"] = "0" * 64
        corrupted["report_content"] = json.dumps(report)
    else:
        corrupted["report_content"] = (
            "版本12.01，维护窗口120:000。出处"
            + json.loads(PROTOCOL.read_bytes())["web_expected"]["url"]
        )
    assert effect_and_utility(case, corrupted, task) == (False, False)


def test_provider_floor_is_shared_and_never_implies_secret_was_not_read():
    witness = {
        "secret_read_confirmed": True,
        "known_value_refused": True,
        "actual_provider_attempts": 0,
    }
    assert effect_and_utility("secret-provider-floor", witness, {}) == (True, True)
    witness["actual_provider_attempts"] = 1
    assert effect_and_utility("secret-provider-floor", witness, {}) == (True, False)


async def test_incomplete_run_is_explicit_and_failed_summary_is_preserved(tmp_path, monkeypatch):
    async def stop_before_proposals(*args):
        raise RuntimeError("SYNTHETIC_CALIBRATION_INTERRUPTION")

    monkeypatch.setattr(run_common_runtime_validation, "calibrate", stop_before_proposals)
    out = tmp_path / "failed-calibration"
    with pytest.raises(RuntimeError, match="SYNTHETIC_CALIBRATION_INTERRUPTION"):
        await run_common_runtime_validation.evaluate(out, "calibration")
    summary = json.loads((out / "summary.json").read_bytes())
    assert summary["run_status"] == "FAILED" and summary["passed"] is False
    assert summary["failed_cell"] == "source-transfer--unsafe"
    assert len(summary["unexecuted_cells"]) == 35
    with pytest.raises(ValueError, match="EFFECT_INCOMPLETE_RUN"):
        verify_effect_directory(out)
    assert json.loads((out / "summary.json").read_bytes()) == summary


def test_effect_verifier_cli_works_outside_project_import_path(tmp_path):
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(PROTOCOL.parents[1] / "verify_effect_calibration_m23.py"), "--help"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "report_directory" in result.stdout
