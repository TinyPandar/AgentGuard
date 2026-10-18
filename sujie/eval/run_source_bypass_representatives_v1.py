"""Fourteen finite source-entry/script/fixed-proposal observations; zero cloud calls."""

import argparse
import asyncio
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / name)
    for name in ("gateway-python/src", "demo-agent", "control-plane-python", "sandbox")
]

from paired_runtime import (  # noqa: E402
    RecordedModel,
    logical_fixture,
    run_model_session,
    verify_pair,
)
from run_parameterized_business_development_v1 import bounded_stop, capture_partial  # noqa: E402
from runtime_source_archive import archive_runtime  # noqa: E402
from source_bypass_recipes import (  # noqa: E402
    CASES,
    TARGET,
    VARIANTS,
    SourceBypassModel,
    SourceBypassSession,
    recipe,
)
from sujie_control.model_runner import ModelCoordinator  # noqa: E402
from sujie_demo_agent.model_budget import BudgetLedger, ModelBudget  # noqa: E402
from sujie_gateway.m1_runtime import new_id, sha  # noqa: E402
from sujie_gateway.model_context import contains_protected  # noqa: E402
from verify_operator_export import verify  # noqa: E402
from verify_sequence_export import recompute  # noqa: E402

PROTOCOL = ROOT / "eval/protocols/source_bypass_representatives_v1.json"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def observe(session):
    trace = session.gateway.trace
    report = session.workspace / "case-001/output/report.txt"
    workflow = session.memory_workflow
    rows, policies = [], {}
    if workflow:
        with closing(sqlite3.connect(workflow.database)) as db:
            rows = [
                {"revision": rev, "content": body, "content_hash": digest}
                for rev, body, digest in db.execute(
                    "SELECT revision,content,content_hash FROM evidence_memory WHERE namespace=? AND key=? ORDER BY revision",
                    (session.id, "asset-note"),
                )
            ]
        policies = {
            phase: json.loads((workflow.root / ("memory-policy-" + phase + ".json")).read_bytes())
            for phase in ("capture", "reconcile")
        }
    content = report.read_bytes().decode() if report.is_file() else ""
    witness = {
        "preparation": session.preparation,
        "final_source_contents": session.source_contents(),
        "direct_content": session.user_message,
        "target_content": (session.workspace / TARGET).read_bytes().decode(),
        "report_present": report.is_file(),
        "report_sha256": sha(content),
        "observed_contents": {
            identifier: trace.artifact_contents[identifier]
            for identifier, artifact in trace.artifacts.items()
            if artifact.to_dict()["origin"]["type"] in {"MCP_TOOL_RESULT", "MEMORY"}
        },
        "memory_rows": rows,
        "memory_policies": policies,
        "receiver_body_sha256": [
            hashlib.sha256(body).hexdigest() for body in session.receiver.bodies
        ],
        "scope": "actual owned-range bytes, trace, Receiver and SQL observations; no signed authenticity or semantic ASR",
    }
    if contains_protected({"content": content, "witness": witness}, (session.honeytoken,)):
        raise ValueError("SOURCE_BYPASS_PROTECTED_OBSERVATION")
    return content, witness


async def evaluate(out):
    from verify_source_bypass_representatives_v1 import recompute_case

    out = Path(out)
    if out.exists():
        raise ValueError("SOURCE_REPORT_ALREADY_EXISTS")
    protocol = json.loads(PROTOCOL.read_bytes())
    if (
        protocol["cases"] != list(CASES)
        or protocol["variants"] != list(VARIANTS)
        or protocol["execution_mode"] != "scripted-fixed-proposal-only"
        or protocol["formal_ready"] is not False
    ):
        raise ValueError("SOURCE_PROTOCOL_INVALID")
    out.mkdir(parents=True)
    archive = archive_runtime(
        out,
        (
            "eval/source_bypass_recipes.py",
            "eval/run_source_bypass_representatives_v1.py",
            "eval/verify_source_bypass_representatives_v1.py",
            "eval/memory_calibration_model.py",
            "eval/delegation_calibration_model.py",
            "eval/paired_runtime.py",
            "eval/runtime_variants.py",
            "eval/run_parameterized_business_development_v1.py",
            "eval/verify_parameterized_business_development_v1.py",
            "eval/verify_core_parameterized_development_v1.py",
            "eval/core_parameterized_tasks.py",
            "eval/parameterized_tasks.py",
            "eval/protocols/source_bypass_representatives_v1.json",
            "tests/test_source_bypass_representatives.py",
        ),
    )
    planned = [case + "--" + variant for case in CASES for variant in VARIANTS]
    budget = ModelBudget(
        ledger=BudgetLedger(out / "provider-budget.sqlite3"),
        max_requests=len(planned) * 12,
        max_units=len(planned) * 200000,
    )
    result = {
        "kind": protocol["kind"],
        "protocol": protocol,
        "protocol_sha256": sha(protocol),
        "runtime_archive_sha256": archive,
        "cloud_calls": 0,
        "formal_ready": False,
        "exposure": "development-exposed",
        "planned_cells": planned,
        "attempted_cells": [],
        "failed_cell_attempts": [],
        "cases": [],
        "paired_checks": [],
        "cleanup_observations": [],
        "run_status": "RUNNING",
        "passed": False,
    }

    def save(refresh=True):
        result["unexecuted_cells"] = [
            name for name in planned if name not in result["attempted_cells"]
        ]
        result["uncompleted_cells"] = [
            name for name in planned if name not in {row["case"] for row in result["cases"]}
        ]
        if refresh:
            result["service_budget"] = budget.view()
        (out / "summary.tmp").write_text(encoded(result), "utf-8")
        (out / "summary.tmp").replace(out / "summary.json")

    save()
    try:
        for case in CASES:
            scope, members = new_id(), []
            for variant in VARIANTS:
                name, models = case + "--" + variant, []
                result["attempted_cells"].append(name)
                save()

                def factory(case_id=case, records=models):
                    return RecordedModel(SourceBypassModel(case_id), records)

                coordinator = ModelCoordinator(factory, "scripted-source-bypass-v1", budget=budget)
                session = SourceBypassSession(
                    case, coordinator, variant=variant, paired_scope_id=scope
                )
                primary_error, task = None, None
                try:
                    await session.start()
                    logical = logical_fixture(session)
                    task = await run_model_session(session, timeout=120)
                    exported = await session.submit("export")
                    content, witness = observe(session)
                    exported["payload"]["source_bypass_witness"] = witness
                    exported["export_hash"] = sha(exported["payload"])
                    verify(exported)
                    recompute(exported)
                    independent = recompute_case(task, witness, content, recipe(case), variant)
                    row = {
                        "case": name,
                        "pair_id": case,
                        "variant": variant,
                        "task_id": session.id,
                        "profile": task["profile"],
                        "fixture": logical,
                        "models": models,
                        "agent": task["agent"],
                        "oracle": task["oracle"],
                        "metrics": task["metrics"],
                        "assessment": independent,
                        "passed": independent["calibration_passed"],
                        "export_hash": exported["export_hash"],
                    }
                    (out / (name + "-report.txt")).write_bytes(content.encode())
                    (out / (name + "-export.json")).write_text(encoded(exported), "utf-8")
                    result["cases"].append(row)
                    members.append(row)
                    save()
                    print(json.dumps({"case": name, **independent}), flush=True)
                except (Exception, asyncio.CancelledError) as error:
                    primary_error = error
                    observed, partial = await capture_partial(session, out, name)
                    task = observed or task
                    result["failed_cell_attempts"].append(
                        {
                            "case": name,
                            "error_type": type(error).__name__,
                            "termination": "CANCELLED"
                            if isinstance(error, asyncio.CancelledError)
                            else "FAILED",
                            "outcome": "unknown-partial-execution",
                            "agent": task["agent"] if task else None,
                            "oracle": task["oracle"] if task else None,
                            "models": models,
                            "partial_export": partial,
                        }
                    )
                    save()
                    raise
                finally:
                    interrupted = await bounded_stop(session)
                    cleaned = (
                        session.worker is not None
                        and session.worker.done()
                        and (session.agent_task is None or session.agent_task.done())
                        and session.cleanup_complete is True
                    )
                    result["cleanup_observations"].append({"case": name, "confirmed": cleaned})
                    save()
                    if primary_error is None and not cleaned:
                        raise RuntimeError("SOURCE_BYPASS_CLEANUP_NOT_CONFIRMED")
                    if primary_error is None and interrupted:
                        raise asyncio.CancelledError
            result["paired_checks"].append(
                {"pair_id": case, **verify_pair(members, require_model=True)}
            )
        result.update(
            run_status="FINISHED",
            passed=len(result["cases"]) == len(planned)
            and all(row["passed"] for row in result["cases"]),
        )
    except (Exception, asyncio.CancelledError) as error:
        result.update(
            run_status="CANCELLED" if isinstance(error, asyncio.CancelledError) else "FAILED",
            error_type=type(error).__name__,
            passed=False,
        )
        raise
    finally:
        save()
        budget.ledger.close()
        result["budget_ledger_sha256"] = hashlib.sha256(
            (out / "provider-budget.sqlite3").read_bytes()
        ).hexdigest()
        save(False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(evaluate(args.out_dir))
    print(json.dumps({key: report[key] for key in ("passed", "run_status", "cloud_calls")}))
    raise SystemExit(int(not report["passed"]))
