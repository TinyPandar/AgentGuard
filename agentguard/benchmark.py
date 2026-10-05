"""Repeatable Unsafe vs Rule Guard vs Full AgentGuard experiments."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .approval import ApprovalService
from .audit import AuditTrace
from .detector import RuleDetector
from .gateway import ToolGateway
from .mock_tools import MockToolEnvironment
from .models import (
    Artifact,
    Authority,
    Delivery,
    RiskLevel,
    Sensitivity,
    SideEffect,
    TaskGrant,
    ToolExecutionResult,
    ToolProposal,
    TrustLevel,
)
from .policy import PolicyEngine


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    benign: bool
    source_type: str
    delivery: Delivery
    content: str
    grant: dict[str, Any]
    proposal: ToolProposal
    artifacts: tuple[Artifact, ...]


def _artifact(payload: dict[str, Any]) -> Artifact:
    return Artifact(
        artifact_id=payload["artifact_id"],
        content=payload.get("content", ""),
        source_type=payload["source_type"],
        source_id=payload["source_id"],
        trust_level=TrustLevel[payload.get("trust_level", "UNTRUSTED")],
        authority=Authority[payload.get("authority", "DATA_ONLY")],
        sensitivity=Sensitivity[payload.get("sensitivity", "PUBLIC")],
        taint_labels=frozenset(payload.get("taint_labels", [])),
        parent_artifact_ids=tuple(payload.get("parent_artifact_ids", [])),
    )


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            proposal = payload["proposal"]
            cases.append(
                BenchmarkCase(
                    case_id=payload["case_id"],
                    category=payload["category"],
                    benign=payload["benign"],
                    source_type=payload["source_type"],
                    delivery=Delivery[payload["delivery"]],
                    content=payload["content"],
                    grant=payload["grant"],
                    proposal=ToolProposal(
                        tool_name=proposal["tool_name"],
                        arguments=proposal["arguments"],
                        resource=proposal.get("resource"),
                        input_artifact_ids=tuple(
                            proposal.get("input_artifact_ids", [])
                        ),
                    ),
                    artifacts=tuple(
                        _artifact(item) for item in payload.get("artifacts", [])
                    ),
                )
            )
    return cases


def _grant(case: BenchmarkCase, trace_id: str) -> TaskGrant:
    payload = case.grant
    return TaskGrant(
        grant_id=f"grant-{trace_id}",
        trace_id=trace_id,
        subject=payload.get("subject", "analyst-1"),
        objective=payload["objective"],
        allowed_tools=frozenset(payload.get("allowed_tools", [])),
        allowed_resources=frozenset(payload.get("allowed_resources", [])),
        permissions=frozenset(payload.get("permissions", [])),
        allowed_data_flows=frozenset(
            tuple(item) for item in payload.get("allowed_data_flows", [])
        ),
        denied_side_effects=frozenset(
            SideEffect[item] for item in payload.get("denied_side_effects", [])
        ),
        max_tool_calls=int(payload.get("max_tool_calls", 5)),
        expires_at=datetime.now(timezone.utc)
        + timedelta(seconds=int(payload.get("ttl_seconds", 600))),
    )


def _blocked(tool_name: str, reason: str) -> ToolExecutionResult:
    return ToolExecutionResult(executed=False, tool_name=tool_name, error=reason)


def run_case(case: BenchmarkCase, mode: str) -> dict[str, Any]:
    environment = MockToolEnvironment()
    registry = environment.registry()
    detector = RuleDetector()
    trace_id = f"{mode}-{case.case_id}"
    scan = detector.scan(
        case.content,
        source_type=case.source_type,
        delivery=case.delivery,
    )

    started = time.perf_counter_ns()
    if mode == "unsafe":
        result = registry.invoke_raw(
            case.proposal.tool_name, case.proposal.arguments, trace_id
        )
    elif mode == "rule_guard":
        spec = registry.get(case.proposal.tool_name)
        if (
            spec is not None
            and scan.risk_level >= RiskLevel.HIGH
            and spec.risk_level >= RiskLevel.HIGH
        ):
            result = _blocked(case.proposal.tool_name, "rule guard blocked request")
        else:
            result = registry.invoke_raw(
                case.proposal.tool_name, case.proposal.arguments, trace_id
            )
    elif mode == "full":
        audit = AuditTrace()
        gateway = ToolGateway(
            registry=registry,
            policy=PolicyEngine(),
            approvals=ApprovalService(),
            audit=audit,
        )
        for artifact in case.artifacts:
            gateway.add_artifact(artifact)
        result = gateway.execute(
            grant=_grant(case, trace_id),
            proposal=case.proposal,
            context_risk=scan.risk_level,
        )
    else:
        raise ValueError(f"unknown benchmark mode: {mode}")
    latency_ms = (time.perf_counter_ns() - started) / 1_000_000

    sensitive_case = any(
        artifact.sensitivity >= Sensitivity.CONFIDENTIAL for artifact in case.artifacts
    )

    return {
        "case_id": case.case_id,
        "category": case.category,
        "benign": case.benign,
        "mode": mode,
        "risk_level": scan.risk_level.name,
        "attack_types": list(scan.attack_types),
        "executed": result.executed,
        "error": result.error,
        "external_messages": len(environment.external_messages),
        "sensitive_case": sensitive_case,
        "latency_ms": round(latency_ms, 4),
    }


def run_benchmark(path: str | Path) -> dict[str, Any]:
    cases = load_cases(path)
    results = [
        run_case(case, mode)
        for mode in ("unsafe", "rule_guard", "full")
        for case in cases
    ]
    metrics: dict[str, dict[str, float | int]] = {}
    for mode in ("unsafe", "rule_guard", "full"):
        mode_results = [item for item in results if item["mode"] == mode]
        attacks = [item for item in mode_results if not item["benign"]]
        benign = [item for item in mode_results if item["benign"]]
        sensitive_cases = [item for item in attacks if item["sensitive_case"]]
        attack_executions = sum(bool(item["executed"]) for item in attacks)
        benign_successes = sum(bool(item["executed"]) for item in benign)
        sensitive_leaks = sum(
            int(item["external_messages"] > 0) for item in sensitive_cases
        )
        ordered_latencies = sorted(float(item["latency_ms"]) for item in mode_results)
        p95_index = max(0, math.ceil(0.95 * len(ordered_latencies)) - 1)
        metrics[mode] = {
            "attack_cases": len(attacks),
            "attack_executions": attack_executions,
            "execution_asr": round(
                attack_executions / len(attacks) if attacks else 0.0, 4
            ),
            "benign_cases": len(benign),
            "benign_successes": benign_successes,
            "normal_task_success_rate": round(
                benign_successes / len(benign) if benign else 0.0, 4
            ),
            "sensitive_flow_cases": len(sensitive_cases),
            "sensitive_leaks": sensitive_leaks,
            "sensitive_leakage_rate": round(
                sensitive_leaks / len(sensitive_cases) if sensitive_cases else 0.0,
                4,
            ),
            "p95_latency_ms": ordered_latencies[p95_index],
        }
    return {"dataset": str(path), "metrics": metrics, "results": results}
