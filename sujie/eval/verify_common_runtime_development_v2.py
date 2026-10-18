"""Recompute v2 development pairing, effects, report hashes and calibration assertions."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / directory)
    for directory in ("gateway-python/src", "demo-agent", "control-plane-python", "sandbox")
]

from paired_runtime import verify_pair  # noqa: E402
from run_common_runtime_development_v2 import (  # noqa: E402
    assess_expectations,
    select_cases,
    validate_protocol,
)
from runtime_variants import VARIANTS, Variant  # noqa: E402
from sujie_gateway.m1_runtime import sha  # noqa: E402
from task_registry import assess_registered_observation  # noqa: E402
from verify_runtime_validation import verify_directory  # noqa: E402


def verify_budget(directory, summary, protocol):
    path = directory / "provider-budget.sqlite3"
    if hashlib.sha256(path.read_bytes()).hexdigest() != summary["budget_ledger_sha256"]:
        raise ValueError("DEVELOPMENT_BUDGET_LEDGER_HASH_MISMATCH")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        maximum = connection.execute(
            "SELECT max_requests,max_units FROM budget_scopes WHERE id='root'"
        ).fetchone()
        rows = connection.execute(
            "SELECT r.purpose,r.status,r.reported_tokens,c.units "
            "FROM model_reservations r JOIN budget_charges c ON c.ticket=r.id "
            "WHERE c.scope='root'"
        ).fetchall()
    finally:
        connection.close()
    planned_count = len(summary["planned_cells"])
    if maximum != (
        planned_count * protocol["task_provider_requests"],
        planned_count * protocol["task_reservation_units"],
    ):
        raise ValueError("DEVELOPMENT_SERVICE_BUDGET_LIMIT_MISMATCH")
    charged = sum(row[3] for row in rows)
    observed = {
        "durable": True,
        "max_requests": maximum[0],
        "requests_reserved": len(rows),
        "remaining_requests": max(0, maximum[0] - len(rows)),
        "max_reservation_units": maximum[1],
        "charged_units": charged,
        "remaining_units": max(0, maximum[1] - charged),
        "reported_tokens": sum(row[2] for row in rows if row[2] is not None),
        "unknown_usage_requests": sum(row[2] is None for row in rows),
        "pending_requests": sum(row[1] == "PENDING" for row in rows),
        "estimate_exceeded": charged > maximum[1],
        "accounting": "LOCAL_ESTIMATE_WITH_PROVIDER_REPORTED_USAGE",
        "billing_bound": "NOT_GUARANTEED",
        "roles": {
            role: sum(row[0] == role for row in rows) for role in sorted({row[0] for row in rows})
        },
    }
    if observed != summary["service_budget"]:
        raise ValueError("DEVELOPMENT_SERVICE_BUDGET_OBSERVATION_MISMATCH")


def verify_development_directory(directory):
    directory = Path(directory)
    integrity = verify_directory(directory)
    summary = json.loads((directory / "summary.json").read_bytes())
    archive = json.loads((directory / "runtime-sources.json").read_bytes())
    protocol_bytes = archive["files"]["eval/protocols/common_runtime_development_v2.json"][
        "utf8"
    ].encode("utf-8")
    registry_bytes = archive["files"]["eval/protocols/core_task_registry_development_v1.json"][
        "utf8"
    ].encode("utf-8")
    protocol, registry = json.loads(protocol_bytes), json.loads(registry_bytes)
    if (
        summary["protocol_file_sha256"] != hashlib.sha256(protocol_bytes).hexdigest()
        or summary["task_registry_sha256"] != hashlib.sha256(registry_bytes).hexdigest()
        or summary["protocol_sha256"] != sha(protocol)
        or summary["protocol"] != protocol
        or summary["cloud_calls"] != 0
        or summary["formal_ready"] is not False
        or summary["exposure"] != "development-exposed"
    ):
        raise ValueError("DEVELOPMENT_SUMMARY_SCOPE_OR_PROTOCOL_MISMATCH")
    validate_protocol(protocol, registry)
    selected = select_cases(protocol, summary["selected_case_ids"])
    selected_ids = [item["case_id"] for item in selected]
    planned_cells = [item["case_id"] + "--" + variant for item in selected for variant in VARIANTS]
    omitted = [item["case_id"] for item in protocol["cases"] if item["case_id"] not in selected_ids]
    if (
        summary["selected_case_ids"] != selected_ids
        or summary["planned_cells"] != planned_cells
        or summary["omitted_protocol_case_ids"] != omitted
        or summary["represented_registered_task_ids"]
        != sorted({item["task_id"] for item in selected if item["task_id"] is not None})
    ):
        raise ValueError("DEVELOPMENT_PROTOCOL_SELECTION_MISMATCH")
    verify_budget(directory, summary, protocol)
    if summary["variant_recipes"] != {name: Variant(name).recipe() for name in VARIANTS}:
        raise ValueError("DEVELOPMENT_VARIANT_RECIPE_MISMATCH")
    specifications = {item["case_id"]: item for item in protocol["cases"]}
    names = set()
    paired = {}
    for row in summary["cases"]:
        name = row["case"]
        if name in names or name not in summary["planned_cells"]:
            raise ValueError("DUPLICATE_OR_UNPLANNED_DEVELOPMENT_CELL")
        names.add(name)
        spec = specifications[row["pair_id"]]
        if (
            name != row["pair_id"] + "--" + row["variant"]
            or any(
                row[key] != spec[key]
                for key in ("profile", "scenario", "scenario_class", "forced_proposals")
            )
            or row["registered_task_id"] != spec["task_id"]
        ):
            raise ValueError("DEVELOPMENT_CASE_MAPPING_MISMATCH")
        exported = json.loads((directory / (name + "-export.json")).read_bytes())
        task = exported["payload"]["task"]
        logical = row["fixture"]["logical"]
        if (
            row["fixture"]["logical_hash"] != sha(logical)
            or logical["profile"] != row["profile"]
            or logical["scenario"] != row["scenario"]
            or any(logical["contract"][key] != task["contract"][key] for key in logical["contract"])
            or any(logical["grant"][key] != task["grant"][key] for key in logical["grant"])
            or any(model["recipe_hash"] != sha(model["recipe"]) for model in row["models"])
        ):
            raise ValueError("DEVELOPMENT_FIXTURE_OR_MODEL_RECIPE_MISMATCH")
        if (
            task["agent"]["budget"]["max_requests"] != protocol["task_provider_requests"]
            or task["agent"]["budget"]["max_reservation_units"]
            != protocol["task_reservation_units"]
        ):
            raise ValueError("DEVELOPMENT_TASK_BUDGET_MISMATCH")
        witness = row["witness"]
        if witness != exported["payload"]["evaluation_development_witness"]:
            raise ValueError("DEVELOPMENT_WITNESS_MISMATCH")
        report_name = witness["report_file"]
        if report_name != name + "-report.txt":
            raise ValueError("DEVELOPMENT_REPORT_PATH_MISMATCH")
        if witness["report_content_hash"] != sha((directory / report_name).read_text("utf-8")):
            raise ValueError("DEVELOPMENT_REPORT_HASH_MISMATCH")
        observed_effects = [
            event
            for event in task["events"]
            if event["event_type"]
            in {"RESOURCE_READ", "RESOURCE_AFFECTED", "EXECUTION_RESULT", "MEMORY_WRITTEN"}
        ]
        if (
            witness["actual_effect_events"] != observed_effects
            or witness["business"] != task["oracle"].get("business")
            or witness["receiver"]["requests"] != task["oracle"]["receiver_requests"]
            or len(witness["receiver"]["body_sha256"]) != task["oracle"]["receiver_requests"]
            or witness["receiver"]["honeytoken_leaked"] != task["oracle"]["honeytoken_leaked"]
            or row["agent"] != task["agent"]
            or row["approvals"] != task["approvals"]
        ):
            raise ValueError("DEVELOPMENT_EFFECT_OR_ORACLE_MISMATCH")
        if witness["business"] is not None:
            inputs = witness["input_content_hashes"]
            reads = witness["business"]["read_source_hashes"]
            if any(inputs.get(key) != value for key, value in reads.items()) or (
                witness["business"]["task_completed"] and reads != inputs
            ):
                raise ValueError("DEVELOPMENT_BUSINESS_READ_HASH_MISMATCH")
        assessment = assess_expectations(task, spec["calibration_expectations"][row["variant"]])
        if assessment != row["calibration_assessment"] or row["passed"] != assessment["passed"]:
            raise ValueError("DEVELOPMENT_CALIBRATION_ASSESSMENT_MISMATCH")
        registered = (
            assess_registered_observation(
                spec["task_id"], task, scenario_class=spec["scenario_class"], registry=registry
            )
            if spec["task_id"] is not None
            else None
        )
        if registered != row["registered_outcome"]:
            raise ValueError("DEVELOPMENT_REGISTERED_OUTCOME_MISMATCH")
        paired.setdefault(row["pair_id"], []).append(row)
    pair_checks = [
        {"pair_id": identifier, **verify_pair(rows, require_model=True)}
        for identifier, rows in paired.items()
        if len(rows) == len(VARIANTS)
    ]
    if pair_checks != summary["paired_checks"]:
        raise ValueError("DEVELOPMENT_PAIRED_CHECK_MISMATCH")
    attempted, planned = set(summary["attempted_cells"]), set(summary["planned_cells"])
    if (
        set(summary["unexecuted_cells"]) != planned - attempted
        or set(summary["uncompleted_cells"]) != planned - names
        or not names <= attempted <= planned
    ):
        raise ValueError("DEVELOPMENT_EXECUTION_ACCOUNTING_MISMATCH")
    passed = (
        len(names) == len(planned)
        and len(pair_checks) == len(summary["selected_case_ids"])
        and all(row["passed"] for row in summary["cases"])
        and not summary["failed_cell_attempts"]
    )
    if summary["passed"] != passed:
        raise ValueError("DEVELOPMENT_PASS_STATUS_MISMATCH")
    if len(names) == len(planned) and not summary["failed_cell_attempts"]:
        for key in (
            "requests_reserved",
            "charged_units",
            "reported_tokens",
            "unknown_usage_requests",
            "pending_requests",
        ):
            if (
                sum(row["agent"]["budget"][key] for row in summary["cases"])
                != summary["service_budget"][key]
            ):
                raise ValueError("DEVELOPMENT_TASK_SERVICE_BUDGET_SUM_MISMATCH")
    return {
        "ok": integrity["ok"],
        "scope": "local archive/export/pairing/development-calibration consistency; not signed authenticity, independent holdout or model ASR",
        "current_sources_match": integrity["current_sources_match"],
        "current_source_mismatches": integrity["current_source_mismatches"],
        "m9_frozen_matches": integrity["m9_frozen_matches"],
        "verified_cells": len(names),
        "verified_pairs": len(pair_checks),
        "recorded_validation_passed": summary["passed"],
        "cloud_calls": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_directory", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = verify_development_directory(args.report_directory)
    if args.out:
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(int(not result["ok"]))
