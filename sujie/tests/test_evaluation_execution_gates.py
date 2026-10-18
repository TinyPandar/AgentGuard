"""Actual MCP side effects survive late errors without becoming normal-run PASS."""

import asyncio
import json
from types import SimpleNamespace

import evidence_quote_calibration as quote
import pytest
import run_business_validation as business
import run_evidence_quote_validation as quote_runner
import run_sequence_calibration as sequence
from business_calibration_model import BusinessCalibrationModel
from sujie_demo_agent.bailian_agent import ModelProtocolError
from sujie_gateway.m1_runtime import new_id
from variant_calibration import calibrate

FAILURE = "M23_FAILURE_AFTER_REPORT"


class BusinessFailsAfterReport(BusinessCalibrationModel):
    async def complete(self, messages, tools):
        if self.calls == 3:
            raise ModelProtocolError(FAILURE)
        return await super().complete(messages, tools)


class SequenceFailsAfterReport(sequence.CalibrationModel):
    async def complete(self, messages, tools):
        if self.calls == 2:
            raise ModelProtocolError(FAILURE)
        return await super().complete(messages, tools)


class SplitSequenceFailsAfterReport(sequence.CalibrationModel):
    """Same four proposals, in three plans, then a failed completion request."""

    async def complete(self, messages, tools):
        if self.calls < 2:
            result = await super().complete(messages, tools)
            if self.calls == 2:
                self.report_call = result["tool_calls"].pop()
            return result
        if self.calls == 2:
            self.calls += 1
            return {"tool_calls": [self.report_call]}
        raise ModelProtocolError(FAILURE)


class QuoteFailsAfterReport(quote.ReportWithQuotes):
    async def complete(self, messages, tools):
        if self.round == 3:
            raise ModelProtocolError(FAILURE)
        return await super().complete(messages, tools)


class QuoteCancelsAfterReport(quote.ReportWithQuotes):
    async def complete(self, messages, tools):
        if self.round == 3:
            raise asyncio.CancelledError
        return await super().complete(messages, tools)


def assert_late_failure(agent):
    assert agent["task_completed"] is True
    assert agent["status"] == "FAILED"
    assert agent["error_code"] == "MODEL_PROTOCOL_ERROR"
    assert agent["model_requests"] == agent["model_responses"] + 1


@pytest.mark.parametrize("fail_index", [0, 3, None], ids=["first", "last", "normal"])
async def test_business_row_and_batch_gate_cover_first_and_last_cloud_branch_cells(
    fail_index, tmp_path, monkeypatch
):
    # Exercise the cloud-mode break/aggregation branch using only local scripted models.
    # The path is never opened, no actual credential or cloud transport is constructed.
    monkeypatch.setattr(
        business,
        "BailianCredentials",
        SimpleNamespace(from_csv=lambda path: SimpleNamespace(api_key="M23-DUMMY-KEY")),
    )
    profiles = json.loads(
        (business.ROOT / "eval/protocols/four_business_workflows_v2.json").read_text("utf-8")
    )["profiles"]
    serial = iter(enumerate(profiles))

    def local_backend(*args, **kwargs):
        index, profile = next(serial)
        backend = BusinessFailsAfterReport if index == fail_index else BusinessCalibrationModel
        return backend(profile)

    monkeypatch.setattr(business, "BailianChatModel", local_backend)
    out = tmp_path / "business"
    report = await business.evaluate(out, tmp_path / "SYNTHETIC_NOT_READ.csv")
    saved = json.loads((out / "summary.json").read_text("utf-8"))
    assert saved == report
    assert report["cloud_calls"] == 0
    assert report["reported_tokens"] == 0
    expected_count = 1 if fail_index == 0 else len(profiles)
    assert len(report["cases"]) == expected_count
    for index, row in enumerate(report["cases"]):
        assert row["agent"]["task_completed"] is True
        assert row["oracle"]["business"]["report_valid"] is True
        assert row["oracle"]["business"]["inputs_unchanged"] is True
        assert row["oracle"]["receiver_requests"] == 0
        assert not row["oracle"]["honeytoken_leaked"]
        assert (out / row["witness"]["report_file"]).read_text("utf-8")
        if index == fail_index:
            assert_late_failure(row["agent"])
            assert row["passed"] is False
        else:
            assert row["agent"]["status"] == "FINISHED"
            assert row["agent"]["error_code"] is None
            assert row["passed"] is True
    assert report["passed"] is (fail_index is None)
    assert report["run_status"] == ("INCOMPLETE" if fail_index == 0 else "FINISHED")
    assert len(report["unexecuted_cells"]) == (3 if fail_index == 0 else 0)


@pytest.mark.parametrize(
    ("backend", "visible_plans", "passed"),
    [
        (SequenceFailsAfterReport, 2, False),
        (SplitSequenceFailsAfterReport, 3, False),
        (sequence.CalibrationModel, 3, True),
    ],
    ids=["grouped-late-failure", "split-late-failure", "normal"],
)
def test_sequence_gate_preserves_tool_trace_and_actual_business_fact(
    backend, visible_plans, passed, tmp_path, monkeypatch
):
    monkeypatch.setattr(sequence, "CalibrationModel", backend)
    out = tmp_path / "sequence"
    report = sequence.evaluate(out)
    assert json.loads((out / "summary.json").read_text("utf-8")) == report
    exported = json.loads((out / "operator-export.json").read_text("utf-8"))
    assert report["agent"] == exported["payload"]["task"]["agent"]
    assert report["task_completed"] is True
    assert report["oracle"]["report_written"] is True
    assert report["oracle"]["receiver_requests"] == 0
    assert not report["oracle"]["honeytoken_leaked"]
    assert report["proposal_count"] == 4
    assert report["visible_plan_count"] == visible_plans
    assert report["blocked_ordinals"] == [2, 3]
    assert report["confirmed_execution_ordinals"] == [1, 4]
    assert report["passed"] is passed
    assert report["cloud_calls"] == 0
    if passed:
        assert report["agent"]["status"] == "FINISHED"
        assert report["agent"]["error_code"] is None
    else:
        assert_late_failure(report["agent"])


@pytest.mark.parametrize(
    ("backend", "expected_status"),
    [
        (QuoteFailsAfterReport, "FAILED"),
        (QuoteCancelsAfterReport, "CANCELLED"),
        (quote.ReportWithQuotes, "FINISHED"),
    ],
    ids=["late-failure", "cancelled", "normal"],
)
async def test_quote_row_and_batch_gate_preserve_exact_original_quotation(
    backend, expected_status, tmp_path, monkeypatch
):
    monkeypatch.setattr(quote, "ReportWithQuotes", backend)
    out = tmp_path / "quote"
    report = await quote_runner.evaluate(out)
    assert json.loads((out / "summary.json").read_text("utf-8")) == report
    row = report["cases"][0]
    assert row["agent"]["task_completed"] is True
    assert row["witness"]["original_unchanged"] is True
    assert row["witness"]["facts_in_report"] is True
    assert row["witness"]["command_in_report"] is True
    assert row["oracle"]["receiver_requests"] == 0
    assert not row["oracle"]["honeytoken_leaked"]
    assert row["passed"] is (expected_status == "FINISHED")
    assert report["passed"] is (expected_status == "FINISHED")
    assert report["cloud_calls"] == 0
    assert row["agent"]["status"] == expected_status
    if expected_status == "FAILED":
        assert_late_failure(row["agent"])
    else:
        assert row["agent"]["error_code"] is None


@pytest.mark.parametrize("missing_error_code", [False, True], ids=["error", "missing-error"])
async def test_finished_state_with_error_or_missing_error_fails_row_and_batch(
    missing_error_code, tmp_path, monkeypatch
):
    # A synthetic Host state fault tests the fail-closed schema contract. The normal
    # runtime does not currently produce these shapes; the report/quotes are real MCP.
    class StateFaultSession(quote.TaskSession):
        async def _run_agent(self, model):
            await super()._run_agent(model)
            if missing_error_code:
                self.agent.pop("error_code")
            else:
                self.agent["error_code"] = "M23_SYNTHETIC_RETAINED_ERROR"

    monkeypatch.setattr(quote, "TaskSession", StateFaultSession)
    report = await quote_runner.evaluate(tmp_path / "quote-state-fault")
    row = report["cases"][0]
    assert row["agent"]["status"] == "FINISHED"
    assert row["agent"]["task_completed"] is True
    assert row["witness"]["command_in_report"] is True
    assert row["witness"]["facts_in_report"] is True
    assert row["witness"]["original_unchanged"] is True
    assert row["passed"] is False
    assert report["passed"] is False
    assert report["cloud_calls"] == 0


async def test_direct_tool_expected_provider_refusal_needs_no_started_model_execution():
    row = await calibrate("full", "secret-provider-floor", new_id())
    assert row["task"]["agent"]["status"] == "NOT_STARTED"
    assert row["actual_provider_attempts"] == 0
    assert row["effect_witness"]["known_value_refused"] is True
    assert row["utility"] is True
    assert row["unsafe_effect"] is False
