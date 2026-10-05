"""The only authorized execution path from an agent to a tool."""

from __future__ import annotations

from collections import defaultdict

from .approval import ApprovalService
from .audit import AuditTrace
from .models import (
    Artifact,
    Decision,
    PolicyDecision,
    RiskLevel,
    TaskGrant,
    ToolExecutionResult,
    ToolProposal,
)
from .policy import PolicyEngine
from .registry import ToolRegistry


class ToolGateway:
    def __init__(
        self,
        *,
        registry: ToolRegistry,
        policy: PolicyEngine,
        approvals: ApprovalService,
        audit: AuditTrace,
    ) -> None:
        self.registry = registry
        self.policy = policy
        self.approvals = approvals
        self.audit = audit
        self.artifacts: dict[str, Artifact] = {}
        self._call_counts: dict[str, int] = defaultdict(int)

    def add_artifact(self, artifact: Artifact) -> None:
        self.artifacts[artifact.artifact_id] = artifact

    def execute(
        self,
        *,
        grant: TaskGrant,
        proposal: ToolProposal,
        context_risk: RiskLevel = RiskLevel.LOW,
        approval_id: str | None = None,
    ) -> ToolExecutionResult:
        trace_id = grant.trace_id
        self.audit.record(
            trace_id,
            "TOOL_PROPOSED",
            tool=proposal.tool_name,
            arguments=proposal.arguments,
            resource=proposal.resource,
            input_artifact_ids=proposal.input_artifact_ids,
        )

        spec = self.registry.get(proposal.tool_name)
        if spec is None:
            return self._deny(trace_id, proposal.tool_name, "unknown tool")
        schema_error = spec.validate_arguments(proposal.arguments)
        if schema_error:
            return self._deny(trace_id, proposal.tool_name, schema_error)

        try:
            input_artifacts = tuple(
                self.artifacts[artifact_id]
                for artifact_id in proposal.input_artifact_ids
            )
        except KeyError as exc:
            return self._deny(
                trace_id,
                proposal.tool_name,
                f"unknown input artifact: {exc.args[0]}",
            )

        decision = self.policy.decide(
            grant=grant,
            proposal=proposal,
            spec=spec,
            artifacts=input_artifacts,
            context_risk=context_risk,
            calls_used=self._call_counts[grant.grant_id],
        )
        self.audit.record(
            trace_id,
            f"POLICY_{decision.decision.value}",
            policy_id=decision.policy_id,
            tool=proposal.tool_name,
            reason=decision.reason,
        )

        if decision.decision is Decision.DENY:
            return ToolExecutionResult(
                executed=False,
                tool_name=proposal.tool_name,
                decision=decision,
                error=decision.reason,
            )
        if decision.decision is Decision.REQUIRE_CONFIRMATION:
            valid, reason = self.approvals.validate_and_consume(
                approval_id,
                trace_id=trace_id,
                subject=grant.subject,
                proposal=proposal,
            )
            if not valid:
                self.audit.record(
                    trace_id,
                    "APPROVAL_REJECTED",
                    tool=proposal.tool_name,
                    reason=reason,
                )
                return ToolExecutionResult(
                    executed=False,
                    tool_name=proposal.tool_name,
                    decision=decision,
                    error=reason,
                )
            self.audit.record(
                trace_id,
                "APPROVAL_ACCEPTED",
                tool=proposal.tool_name,
                approval_id=approval_id,
            )

        result = spec.handler(proposal.arguments, trace_id)
        if result.executed:
            self._call_counts[grant.grant_id] += 1
            for artifact in result.artifacts:
                self.add_artifact(artifact)
            self.audit.record(
                trace_id,
                "TOOL_EXECUTED",
                tool=proposal.tool_name,
                produced_artifacts=[a.artifact_id for a in result.artifacts],
            )
        else:
            self.audit.record(
                trace_id,
                "TOOL_FAILED",
                tool=proposal.tool_name,
                error=result.error,
            )
        return result

    def _deny(self, trace_id: str, tool_name: str, reason: str) -> ToolExecutionResult:
        decision = PolicyDecision(Decision.DENY, self.policy.POLICY_ID, reason)
        self.audit.record(
            trace_id,
            "POLICY_DENY",
            policy_id=decision.policy_id,
            tool=tool_name,
            reason=reason,
        )
        return ToolExecutionResult(
            executed=False,
            tool_name=tool_name,
            decision=decision,
            error=reason,
        )
