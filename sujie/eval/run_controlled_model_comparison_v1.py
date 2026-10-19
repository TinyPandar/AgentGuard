"""Observational exposed comparison with complete records, not efficacy pass gates."""

import argparse
import asyncio
import base64
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / name)
    for name in ("gateway-python/src", "demo-agent", "control-plane-python", "sandbox")
]

from core_parameterized_tasks import BUSINESS_PROFILES, load_sealed_instances  # noqa: E402
from delegated_instance_model import DelegatedInstanceModel  # noqa: E402
from evaluation_models import calibration_backend  # noqa: E402
from model_comparison_observations import assess, initial_snapshot, observe  # noqa: E402
from model_comparison_protocol import (  # noqa: E402
    encoded,
    load_protocol,
    planned_cells,
    planned_pairs,
)
from paired_runtime import (  # noqa: E402
    RecordedModel,
    logical_fixture,
    run_model_session,
    verify_pair,
)
from run_parameterized_business_development_v1 import bounded_stop, capture_partial  # noqa: E402
from runtime_source_archive import archive_runtime  # noqa: E402
from runtime_variants import TrialTaskSession, Variant  # noqa: E402
from sujie_control.model_runner import ModelCoordinator  # noqa: E402
from sujie_demo_agent.bailian_agent import supports_prepared_requests  # noqa: E402
from sujie_demo_agent.model_budget import BudgetLedger, ModelBudget  # noqa: E402
from sujie_gateway.m1_runtime import new_id, sha  # noqa: E402
from sujie_gateway.model_context import canonical, contains_protected  # noqa: E402
from verify_operator_export import verify  # noqa: E402
from verify_sequence_export import recompute  # noqa: E402


class EvidenceRecordedModel(RecordedModel):
    """Only this new experiment retains checked request bytes for offline recomputation."""

    def __init__(self, backend, records, protected_values):
        super().__init__(backend, records)
        self.protected_values = protected_values

    def _check_recipe(self):
        try:
            return super()._check_recipe()
        except ValueError:
            self.node["integrity_error"] = "PAIRED_MODEL_CONFIGURATION_DRIFT"
            raise

    def _record(self, messages, tools, *, prepared=None):
        payload = canonical({"messages": messages, "tools": tools})
        wire = prepared.wire_json if prepared else None
        if contains_protected(
            {"messages_tools": payload, "effective_body": wire}, self.protected_values
        ):
            raise ValueError("COMPARISON_PROTECTED_REQUEST_WITNESS")
        record = super()._record(messages, tools, prepared=prepared)
        record["messages_tools_b64"] = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        record["effective_body_b64"] = (
            base64.b64encode(wire.encode("utf-8")).decode("ascii") if wire else None
        )
        return record


def bind_model_records(models, task, context_audit):
    raw_events = {event["event_id"]: event for event in task["events"]}
    events = []
    for row in context_audit["records"]:
        if row["event_type"] != "MODEL_REQUEST_CHECKED":
            continue
        event = raw_events[row["event_id"]]
        if (
            event["actor_id"] != row["subject_id"]
            or event["sequence"] != row["sequence"]
            or event["payload_hash"] != sha(row["metadata"])
        ):
            raise ValueError("COMPARISON_MODEL_AUDIT_MISMATCH")
        events.append(event | {"details": row["metadata"]})
    consumed = set()
    roles = {task["grant"]["subject_id"]: ("MAIN", task["contract"]["session_id"])}
    roles.update(
        {
            node["subject_id"]: (node["role"], task["contract"]["session_id"])
            for node in task.get("delegations", [])
        }
    )
    roles.update(
        {
            node["grant"]["subject_id"]: (node["name"], node["session_id"])
            for node in task.get("memory_sessions", [])
        }
    )
    for model in models:
        for request in model["requests"]:
            candidates = [
                event
                for event in events
                if event["event_id"] not in consumed
                and (
                    event["details"].get("call_id") == request["call_id"]
                    if request["call_id"]
                    else event["details"].get("request_hash") == request["content_hash"]
                )
            ]
            if not candidates:
                raise ValueError("COMPARISON_MODEL_EVENT_BINDING_MISSING")
            event = candidates[0]
            consumed.add(event["event_id"])
            role, session = roles[event["actor_id"]]
            request.update(
                actor_id=event["actor_id"],
                role=role,
                role_session_id=session,
                purpose=event["details"]["purpose"],
                call_id=event["details"]["call_id"],
                budget_ticket=event["details"]["budget_ticket"],
            )
        model["actor_ids"] = sorted({item["actor_id"] for item in model["requests"]})
    if len(consumed) != len(events) or any(node.get("integrity_error") for node in models):
        raise ValueError("COMPARISON_MODEL_EVENT_MAPPING_INVALID")


def compare_pair(rows, pair_id):
    result = verify_pair(rows, require_model=False)
    initial = [row["models"][0] for row in rows if row["models"] and row["models"][0]["requests"]]
    if len(initial) == len(rows):
        result = verify_pair(rows, require_model=True)
    else:
        if initial and (
            len({model["recipe_hash"] for model in initial}) != 1
            or len({model["requests"][0]["content_hash"] for model in initial}) != 1
        ):
            raise ValueError("COMPARISON_PARTIAL_PAIR_DRIFT")
        result["reason"] = "ONE_OR_MORE_CELLS_HAVE_NO_INITIAL_MODEL_REQUEST"
    return {"pair_id": pair_id, **result}


def budget_limits(protocol, count, requests=None, units=None):
    maximum_requests, maximum_units = count * 12, count * 200000
    requests = maximum_requests if requests is None else requests
    units = maximum_units if units is None else units
    if (
        type(requests) is not int
        or not 1 <= requests <= maximum_requests
        or type(units) is not int
        or not 1 <= units <= maximum_units
        or maximum_requests > protocol["maximum_global_requests"]
        or maximum_units > protocol["maximum_global_reservation_units"]
    ):
        raise ValueError("COMPARISON_GLOBAL_BUDGET_INVALID")
    return {
        "max_requests": requests,
        "max_units": units,
        "task_requests": 12,
        "task_units": 200000,
        "billing_bound": "NOT_GUARANTEED",
    }


def _default_backend(profile):
    return (
        DelegatedInstanceModel() if profile == "delegated-report" else calibration_backend(profile)
    )


def _offline_recipe(backend, protocol):
    from offline_model_comparison_http import closed_transport_admitted

    recipe = protocol["model_recipe"]
    if (
        not closed_transport_admitted(backend)
        or not supports_prepared_requests(backend)
        or backend.model != recipe["model"]
        or backend.max_tokens != recipe["max_tokens"]
        or backend.temperature != recipe["temperature"]
        or backend.tool_choice != recipe["tool_choice"]
        or backend.timeout != recipe["request_timeout_seconds"]
    ):
        raise ValueError("COMPARISON_OFFLINE_MODEL_RECIPE_INVALID")


def global_budget_blocked(task, context_audit, shared):
    """Compare the global remainder with every evidenced local ancestor cap."""
    main = task["grant"]["subject_id"]
    local = {main: (None, task["agent"].get("budget", {}))}
    ambiguous = set()
    for node in task.get("delegations", []):
        actor = node["subject_id"]
        if actor in local:
            ambiguous.add(actor)
        local[actor] = (node.get("parent_subject_id"), node.get("model_budget", {}))
    for node in task.get("memory_sessions", []):
        actor = node["grant"]["subject_id"]
        if actor in local:
            ambiguous.add(actor)
        local[actor] = (main, node.get("budget", {}))

    def local_minimum(actor, dimension):
        remaining, seen = [], set()
        while actor not in seen:
            if actor not in local or actor in ambiguous:
                return None
            seen.add(actor)
            parent, budget = local[actor]
            value = budget.get(dimension)
            if type(value) is not int or value < 0:
                return None
            remaining.append(value)
            if actor == main:
                return min(remaining)
            actor = parent
        return None

    for row in context_audit["records"]:
        if row["event_type"] != "MODEL_EGRESS_BLOCKED":
            continue
        code = row["metadata"].get("code")
        dimension = {
            "MODEL_BUDGET_REQUESTS_EXHAUSTED": "remaining_requests",
            "MODEL_BUDGET_UNITS_EXHAUSTED": "remaining_units",
        }.get(code)
        if not dimension:
            continue
        smallest_local = local_minimum(row["subject_id"], dimension)
        global_remaining = shared.get(dimension)
        if (
            smallest_local is not None
            and type(global_remaining) is int
            and 0 <= global_remaining <= smallest_local
        ):
            return True
    return False


async def evaluate(
    out,
    *,
    instance_dir,
    selected_pair_ids=None,
    execution_mode="scripted-only",
    backend_factory=None,
    total_request_limit=None,
    total_unit_limit=None,
):
    protocol = load_protocol()
    if execution_mode not in protocol["allowed_execution_modes"]:
        raise ValueError("COMPARISON_LIVE_PROVIDER_DISABLED_NO_CREDENTIAL_READ")
    if execution_mode == "offline-http" and backend_factory is None:
        raise ValueError("COMPARISON_OFFLINE_FACTORY_REQUIRED")
    out, instance_dir = Path(out), Path(instance_dir)
    if out.exists():
        raise ValueError("REPORT_ALREADY_EXISTS")
    index, instances = load_sealed_instances(instance_dir)
    pairs = planned_pairs(protocol, instances, selected_pair_ids)
    planned = planned_cells(pairs)
    limits = budget_limits(protocol, len(planned), total_request_limit, total_unit_limit)
    out.mkdir(parents=True)
    shutil.copytree(instance_dir, out / "sealed-inputs")
    archive = archive_runtime(
        out,
        (
            "eval/model_comparison_protocol.py",
            "eval/model_comparison_observations.py",
            "eval/offline_model_comparison_http.py",
            "eval/run_controlled_model_comparison_v1.py",
            "eval/verify_controlled_model_comparison_v1.py",
            "eval/protocols/controlled_model_comparison_development_v1.json",
            "eval/core_parameterized_tasks.py",
            "eval/parameterized_tasks.py",
            "eval/core_calibration_observations.py",
            "eval/evaluation_models.py",
            "eval/git_instance_model.py",
            "eval/delegated_instance_model.py",
            "eval/delegation_calibration_model.py",
            "eval/memory_calibration_model.py",
            "eval/business_calibration_model.py",
            "eval/run_git_validation.py",
            "eval/run_web_validation.py",
            "eval/run_artifact_validation.py",
            "eval/paired_runtime.py",
            "eval/runtime_variants.py",
            "eval/run_parameterized_business_development_v1.py",
            "eval/verify_parameterized_business_development_v1.py",
            "eval/verify_core_parameterized_development_v1.py",
            "eval/verify_runtime_validation.py",
            "tests/test_model_comparison_runner.py",
            "tests/test_model_comparison_http.py",
            "tests/test_model_comparison_observations.py",
            "tests/test_model_comparison_verifier.py",
            "tests/test_comparison_budget_ancestors.py",
        ),
    )
    source_map = json.loads((out / "runtime-sources.json").read_bytes())["files"]

    def check_sources():
        if any(
            not (ROOT / name).is_file()
            or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != row["sha256"]
            for name, row in source_map.items()
        ):
            raise ValueError("COMPARISON_SOURCE_OR_PROTOCOL_CHANGED")

    budget = ModelBudget(
        ledger=BudgetLedger(out / "provider-budget.sqlite3"),
        max_requests=limits["max_requests"],
        max_units=limits["max_units"],
    )
    variants = sorted({variant for pair in pairs for variant in pair["variants"]})
    result = {
        "kind": protocol["kind"],
        "experiment_mode": "observational",
        "exposure": "development-exposed",
        "formal_ready": False,
        "execution_mode": execution_mode,
        "cloud_calls": 0,
        "provider_transport_attempts": 0,
        "runtime_archive_sha256": archive,
        "protocol": protocol,
        "protocol_sha256": sha(protocol),
        "budget_limits": limits,
        "manifest_index_sha256": hashlib.sha256(
            (out / "sealed-inputs/manifest-index.json").read_bytes()
        ).hexdigest(),
        "sealed_manifest_index": index,
        "variant_recipes": {name: Variant(name).recipe() for name in variants},
        "selected_pair_ids": [pair["pair_id"] for pair in pairs],
        "omitted_protocol_pair_ids": [
            pair["pair_id"] for pair in protocol["pairs"] if pair not in pairs
        ],
        "planned_cells": planned,
        "execution_order": planned[:],
        "attempted_cells": [],
        "unexecuted_cells": planned[:],
        "uncompleted_cells": planned[:],
        "cases": [],
        "failed_cell_attempts": [],
        "cleanup_observations": [],
        "paired_checks": [],
        "run_status": "RUNNING",
        "records_valid": False,
        "passed": False,
        "pass_scope": "complete observational records only; agent failures and actual unsafe effects do not invalidate a complete record",
        "task_count_scope": protocol["task_count_scope"],
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
        tmp = out / "summary.tmp"
        tmp.write_text(encoded(result), encoding="utf-8")
        tmp.replace(out / "summary.json")

    save()
    try:
        for pair in pairs:
            instance, paired_id, members = instances[pair["instance_id"]], new_id(), []
            for variant in pair["variants"]:
                check_sources()
                name = pair["pair_id"] + "--" + variant
                available = budget.view()
                if available["remaining_requests"] == 0 or available["remaining_units"] == 0:
                    result.update(
                        run_status="BUDGET_EXHAUSTED", stop_reason="GLOBAL_BUDGET_EXHAUSTED"
                    )
                    save()
                    return result
                result["attempted_cells"].append(name)
                result["running_cell"] = name
                save()
                models, backends, factory_errors = [], [], []

                def backend(
                    profile=instance["profile"],
                    records=models,
                    actual=backends,
                    errors=factory_errors,
                ):
                    model = (
                        backend_factory(profile) if backend_factory else _default_backend(profile)
                    )
                    if execution_mode == "scripted-only" and supports_prepared_requests(model):
                        errors.append("COMPARISON_PREPARED_PROVIDER_FORBIDDEN_IN_SCRIPTED_MODE")
                        raise ValueError(errors[-1])
                    if execution_mode == "offline-http":
                        try:
                            _offline_recipe(model, protocol)
                        except ValueError as error:
                            errors.append(str(error))
                            raise
                    actual.append(model)
                    return EvidenceRecordedModel(model, records, (session.honeytoken,))

                coordinator = ModelCoordinator(
                    backend,
                    "scripted-controlled-comparison-v1"
                    if execution_mode == "scripted-only"
                    else protocol["model_recipe"]["model"],
                    budget=budget,
                    max_runs=len(planned),
                )
                kwargs = {
                    "business_instance"
                    if instance["profile"] in BUSINESS_PROFILES
                    else "core_instance": instance
                }
                session = TrialTaskSession(
                    "同事实受控观察性开发比较",
                    instance["profile"],
                    pair["scenario"],
                    coordinator,
                    variant=variant,
                    paired_scope_id=paired_id,
                    **kwargs,
                )
                task, primary_error, global_blocked = None, None, False
                try:
                    await session.start()
                    fixture, initial = logical_fixture(session), initial_snapshot(session)
                    task = await run_model_session(
                        session, timeout=protocol["session_timeout_seconds"]
                    )
                    exported = await session.submit("export")
                    report, witness = observe(session, task, initial)
                    if factory_errors:
                        raise ValueError(factory_errors[0])
                    bind_model_records(models, task, exported["payload"]["context_audit"])
                    for node, actual in zip(models, backends, strict=True):
                        attempts = getattr(actual, "transport_attempts", 0)
                        if (
                            type(attempts) is not int
                            or attempts < 0
                            or attempts > len(node["requests"])
                            or execution_mode == "scripted-only"
                            and attempts
                        ):
                            raise ValueError("COMPARISON_TRANSPORT_COUNTER_INVALID")
                        node["provider_transport_attempts"] = attempts
                    attempts = sum(node["provider_transport_attempts"] for node in models)
                    if contains_protected(
                        {"models": models, "witness": witness, "report": report},
                        (session.honeytoken,),
                    ):
                        raise ValueError("COMPARISON_PROTECTED_PUBLIC_EVIDENCE")
                    exported["payload"]["model_comparison_witness"] = witness
                    exported["export_hash"] = sha(exported["payload"])
                    verify(exported)
                    recompute(exported)
                    assessment = assess(task, witness)
                    global_blocked = global_budget_blocked(
                        task, exported["payload"]["context_audit"], budget.view()
                    )
                    row = {
                        "case": name,
                        "pair_id": pair["pair_id"],
                        "instance_id": pair["instance_id"],
                        "fact_group_id": pair["fact_group_id"],
                        "profile": instance["profile"],
                        "scenario": pair["scenario"],
                        "classes": pair["classes"],
                        "variant": variant,
                        "task_id": session.id,
                        "fixture": fixture,
                        "models": models,
                        "agent": task["agent"],
                        "oracle": task["oracle"],
                        "metrics": task["metrics"],
                        "witness": witness,
                        "assessment": assessment,
                        "record_valid": True,
                        "observation_complete": True,
                        "export_hash": exported["export_hash"],
                        "provider_transport_attempts": attempts,
                    }
                    (out / (name + "-report.txt")).write_bytes(report.encode("utf-8"))
                    (out / (name + "-export.json")).write_text(encoded(exported), encoding="utf-8")
                    result["cases"].append(row)
                    members.append(row)
                    save()
                    print(
                        json.dumps({"case": name, "record_valid": True, **assessment}), flush=True
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
                            "unsafe_effect_observed": None,
                        }
                    )
                    save()
                    raise
                finally:
                    interrupted = await bounded_stop(session)
                    worker, agent = (
                        getattr(session, "worker", None),
                        getattr(session, "agent_task", None),
                    )
                    cleaned = (
                        worker is not None
                        and worker.done()
                        and (agent is None or agent.done())
                        and getattr(session, "cleanup_complete", False) is True
                    )
                    attempts = 0
                    for node, actual in zip(models, backends, strict=True):
                        counter = getattr(actual, "transport_attempts", 0)
                        if type(counter) is not int or counter < 0:
                            raise ValueError("COMPARISON_TRANSPORT_COUNTER_INVALID")
                        node["provider_transport_attempts"] = counter
                        attempts += counter
                    result["provider_transport_attempts"] += attempts
                    if (
                        result["failed_cell_attempts"]
                        and result["failed_cell_attempts"][-1]["case"] == name
                    ):
                        result["failed_cell_attempts"][-1]["provider_transport_attempts"] = attempts
                    result["cleanup_observations"].append(
                        {
                            "case": name,
                            "owned_worker_and_contexts_closed": cleaned,
                            "scope": "owned asyncio worker/agent and AsyncExitStack exit; not OS process isolation",
                        }
                    )
                    save()
                    if not cleaned and primary_error is None:
                        raise RuntimeError("COMPARISON_CLEANUP_NOT_CONFIRMED")
                    if interrupted and primary_error is None:
                        raise asyncio.CancelledError
                if global_blocked:
                    result.update(
                        run_status="BUDGET_EXHAUSTED", stop_reason="GLOBAL_BUDGET_ADMISSION_FAILED"
                    )
                    save()
                    return result
            result["paired_checks"].append(compare_pair(members, pair["pair_id"]))
            save()
        check_sources()
        result.update(
            run_status="FINISHED",
            records_valid=len(result["cases"]) == len(planned),
            passed=len(result["cases"]) == len(planned),
        )
    except (Exception, asyncio.CancelledError) as error:
        result.update(
            run_status="CANCELLED" if isinstance(error, asyncio.CancelledError) else "FAILED",
            error_type=type(error).__name__,
            stop_reason="OPERATOR_CANCELLED"
            if isinstance(error, asyncio.CancelledError)
            else (
                str(error)
                if re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", str(error))
                else "COMPARISON_INTEGRITY_EXCEPTION"
            ),
            records_valid=False,
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--instance-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", dest="pairs")
    parser.add_argument(
        "--mode", choices=("scripted-only", "offline-http"), default="scripted-only"
    )
    parser.add_argument("--request-limit", type=int)
    parser.add_argument("--unit-limit", type=int)
    args = parser.parse_args()
    kwargs = dict(
        instance_dir=args.instance_dir,
        selected_pair_ids=args.pairs,
        execution_mode=args.mode,
        total_request_limit=args.request_limit,
        total_unit_limit=args.unit_limit,
    )
    if args.mode == "offline-http":
        from offline_model_comparison_http import offline_factory

        protocol = load_protocol()
        with offline_factory(protocol["model_recipe"]) as factory:
            result = asyncio.run(evaluate(args.out_dir, backend_factory=factory, **kwargs))
    else:
        result = asyncio.run(evaluate(args.out_dir, **kwargs))
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "run_status",
                    "records_valid",
                    "cloud_calls",
                    "provider_transport_attempts",
                )
            }
        )
    )
    return int(not result["records_valid"])


if __name__ == "__main__":
    raise SystemExit(main())
