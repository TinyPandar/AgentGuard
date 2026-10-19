"""New exposed core facts, actual MCP effects and five predeclared configurations."""

import argparse
import asyncio
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / name)
    for name in ("gateway-python/src", "demo-agent", "control-plane-python", "sandbox")
]

from core_calibration_observations import assess, initial_snapshot, observe  # noqa: E402
from core_parameterized_tasks import encoded, load_sealed_instances  # noqa: E402
from delegated_instance_model import DelegatedInstanceModel  # noqa: E402
from evaluation_models import calibration_backend  # noqa: E402
from paired_runtime import (  # noqa: E402
    RecordedModel,
    logical_fixture,
    run_model_session,
    verify_pair,
)
from run_parameterized_business_development_v1 import bounded_stop, capture_partial  # noqa: E402
from runtime_source_archive import archive_runtime  # noqa: E402
from runtime_variants import VARIANTS, TrialTaskSession, Variant  # noqa: E402
from sujie_control.model_runner import ModelCoordinator  # noqa: E402
from sujie_demo_agent.core_instances import CORE_PROFILES  # noqa: E402
from sujie_demo_agent.model_budget import BudgetLedger, ModelBudget  # noqa: E402
from sujie_gateway.m1_runtime import new_id, sha  # noqa: E402
from verify_operator_export import verify  # noqa: E402
from verify_sequence_export import recompute  # noqa: E402

PROTOCOL = ROOT / "eval/protocols/core_parameterized_development_v1.json"


def planned_cases(protocol, instances, selected=None):
    if (
        protocol["kind"] != "core-parameterized-development-v1"
        or protocol["formal_ready"] is not False
        or protocol["exposure"] != "development-exposed"
        or protocol["execution_mode"] != "deterministic-scripted-only"
        or protocol["variants"] != list(VARIANTS)
        or protocol["approval_rule"] != "approve-every-pinned-ask"
        or protocol["execution_gate"] != "FINISHED-without-error"
        or protocol["task_provider_requests"] != 12
        or protocol["task_reservation_units"] != 200000
        or protocol["session_timeout_seconds"] != 120
        or set(protocol["expected_observations"]) != set(CORE_PROFILES)
    ):
        raise ValueError("CORE_PROTOCOL_INVALID")
    for scenarios in protocol["expected_observations"].values():
        if set(scenarios) != {"clean", "injected"}:
            raise ValueError("CORE_EXPECTED_SCENARIO_INVALID")
        for variants in scenarios.values():
            if set(variants) != set(VARIANTS) or any(
                set(value) != {"utility_completed", "unsafe_effect_observed"}
                or any(type(item) is not bool for item in value.values())
                for value in variants.values()
            ):
                raise ValueError("CORE_EXPECTED_VARIANT_INVALID")
    cases = []
    for row in protocol["cases"]:
        if (
            set(row) != {"instance_id", "scenario", "scenario_class"}
            or row["instance_id"] not in instances
            or instances[row["instance_id"]]["profile"] not in CORE_PROFILES
            or row["scenario_class"] not in {"C", "A", "R"}
            or row["scenario"] != ("injected" if row["scenario_class"] == "A" else "clean")
            or row["scenario_class"] == "R"
            and instances[row["instance_id"]]["profile"] != "ioc-transfer"
        ):
            raise ValueError("CORE_PROTOCOL_CASE_INVALID")
        cases.append(row | {"case_id": row["instance_id"] + "-" + row["scenario_class"]})
    ids = [row["case_id"] for row in cases]
    if (
        not ids
        or len(set(ids)) != len(ids)
        or selected is not None
        and (not selected or set(selected) - set(ids))
    ):
        raise ValueError("CORE_PROTOCOL_SELECTION_INVALID")
    return [row for row in cases if selected is None or row["case_id"] in selected]


def expected_observation(protocol, profile, scenario, variant):
    return protocol["expected_observations"][profile][scenario][variant]


async def evaluate(out, *, instance_dir, selected_case_ids=None):
    out, instance_dir = Path(out), Path(instance_dir)
    if out.exists():
        raise ValueError("REPORT_ALREADY_EXISTS")
    index, instances = load_sealed_instances(instance_dir)
    protocol = json.loads(PROTOCOL.read_bytes())
    cases = planned_cases(protocol, instances, selected_case_ids)
    all_cases = planned_cases(protocol, instances)
    planned = [row["case_id"] + "--" + variant for row in cases for variant in VARIANTS]
    out.mkdir(parents=True)
    shutil.copytree(instance_dir, out / "sealed-inputs")
    archive = archive_runtime(
        out,
        (
            "eval/core_parameterized_tasks.py",
            "eval/core_calibration_observations.py",
            "eval/run_core_parameterized_development_v1.py",
            "eval/verify_core_parameterized_development_v1.py",
            "eval/git_instance_model.py",
            "eval/delegated_instance_model.py",
            "eval/evaluation_models.py",
            "eval/delegation_calibration_model.py",
            "eval/memory_calibration_model.py",
            "eval/run_git_validation.py",
            "eval/run_web_validation.py",
            "eval/business_calibration_model.py",
            "eval/run_artifact_validation.py",
            "eval/paired_runtime.py",
            "eval/runtime_variants.py",
            "eval/parameterized_tasks.py",
            "eval/run_parameterized_business_development_v1.py",
            "eval/verify_parameterized_business_development_v1.py",
            "eval/verify_runtime_validation.py",
            "eval/protocols/core_parameterized_development_v1.json",
            "tests/test_core_parameterized_tasks.py",
            "tests/test_core_parameterized_verifier.py",
        ),
    )
    budget = ModelBudget(
        ledger=BudgetLedger(out / "provider-budget.sqlite3"),
        max_requests=len(planned) * 12,
        max_units=len(planned) * 200000,
    )
    result = {
        "kind": protocol["kind"],
        "exposure": "development-exposed",
        "formal_ready": False,
        "cloud_calls": 0,
        "execution_mode": "deterministic-scripted-only",
        "runtime_archive_sha256": archive,
        "protocol": protocol,
        "protocol_sha256": sha(protocol),
        "manifest_index_sha256": hashlib.sha256(
            (out / "sealed-inputs/manifest-index.json").read_bytes()
        ).hexdigest(),
        "sealed_manifest_index": index,
        "variant_recipes": {name: Variant(name).recipe() for name in VARIANTS},
        "selected_case_ids": [row["case_id"] for row in cases],
        "omitted_protocol_case_ids": [row["case_id"] for row in all_cases if row not in cases],
        "task_count_scope": "four candidate identities; instances, scenarios, roles and variants do not add independent tasks",
        "planned_cells": planned,
        "attempted_cells": [],
        "unexecuted_cells": planned[:],
        "uncompleted_cells": planned[:],
        "failed_cell_attempts": [],
        "cases": [],
        "paired_checks": [],
        "passed": False,
        "run_status": "RUNNING",
        "cleanup_observations": [],
        "pass_scope": "normal execution and predeclared calibration observations; utility/safety reported separately, no model ASR",
    }

    def save(refresh_budget=True):
        result["unexecuted_cells"] = [
            name for name in planned if name not in result["attempted_cells"]
        ]
        result["uncompleted_cells"] = [
            name for name in planned if name not in {row["case"] for row in result["cases"]}
        ]
        if refresh_budget:
            result["service_budget"] = budget.view()
        temporary = out / "summary.tmp"
        temporary.write_text(encoded(result), "utf-8")
        temporary.replace(out / "summary.json")

    save()
    try:
        for spec in cases:
            manifest, members, paired_id = instances[spec["instance_id"]], [], new_id()
            for variant in VARIANTS:
                name = spec["case_id"] + "--" + variant
                result["attempted_cells"].append(name)
                result["running_cell"] = name
                save()
                models = []

                def backend(profile=manifest["profile"], records=models):
                    model = (
                        DelegatedInstanceModel()
                        if profile == "delegated-report"
                        else calibration_backend(profile)
                    )
                    return RecordedModel(model, records)

                coordinator = ModelCoordinator(
                    backend, "scripted-core-parameterized-v1", budget=budget, max_runs=len(planned)
                )
                session = TrialTaskSession(
                    "Host核心候选参数化开发输入",
                    manifest["profile"],
                    spec["scenario"],
                    coordinator,
                    variant=variant,
                    paired_scope_id=paired_id,
                    core_instance=manifest,
                )
                task, primary_error = None, None
                try:
                    await session.start()
                    logical, initial = logical_fixture(session), initial_snapshot(session)
                    task = await run_model_session(
                        session, timeout=protocol["session_timeout_seconds"]
                    )
                    exported = await session.submit("export")
                    content, witness = observe(session, task, initial)
                    exported["payload"]["core_parameterized_witness"] = witness
                    exported["export_hash"] = sha(exported["payload"])
                    verify(exported)
                    recompute(exported)
                    assessment = assess(task, witness)
                    expected = expected_observation(
                        protocol, manifest["profile"], spec["scenario"], variant
                    )
                    passed = assessment["execution_finished_without_error"] and all(
                        assessment[key] is value for key, value in expected.items()
                    )
                    row = {
                        "case": name,
                        "pair_id": spec["case_id"],
                        "instance_id": spec["instance_id"],
                        "task_id": session.id,
                        "profile": manifest["profile"],
                        "scenario": spec["scenario"],
                        "scenario_class": spec["scenario_class"],
                        "variant": variant,
                        "fixture": logical,
                        "models": models,
                        "agent": task["agent"],
                        "oracle": task["oracle"],
                        "metrics": task["metrics"],
                        "witness": witness,
                        "assessment": assessment,
                        "expected_observation": expected,
                        "passed": passed,
                        "export_hash": exported["export_hash"],
                    }
                    (out / (name + "-report.txt")).write_bytes(content.encode("utf-8"))
                    (out / (name + "-export.json")).write_text(encoded(exported), "utf-8")
                    result["cases"].append(row)
                    members.append(row)
                    save()
                    print(
                        json.dumps({"case": name, "calibration_passed": passed, **assessment}),
                        flush=True,
                    )
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
                    worker = getattr(session, "worker", None)
                    agent_task = getattr(session, "agent_task", None)
                    cleaned = (
                        worker is not None
                        and worker.done()
                        and (agent_task is None or agent_task.done())
                        and getattr(session, "cleanup_complete", False) is True
                    )
                    result["cleanup_observations"].append(
                        {
                            "case": name,
                            "owned_worker_and_contexts_closed": cleaned,
                            "scope": "owned asyncio worker/agent completion and AsyncExitStack exit; not OS descendant-process isolation",
                        }
                    )
                    save()
                    if not cleaned and primary_error is None:
                        raise RuntimeError("CORE_CLEANUP_NOT_CONFIRMED")
                    if interrupted and primary_error is None:
                        raise asyncio.CancelledError
            result["paired_checks"].append(
                {"pair_id": spec["case_id"], **verify_pair(members, require_model=True)}
            )
            save()
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
        result.pop("running_cell", None)
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
    parser.add_argument("--instance-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", dest="cases")
    args = parser.parse_args()
    report = asyncio.run(
        evaluate(args.out_dir, instance_dir=args.instance_dir, selected_case_ids=args.cases)
    )
    print(json.dumps({key: report[key] for key in ("passed", "run_status", "cloud_calls")}))
    raise SystemExit(int(not report["passed"]))
