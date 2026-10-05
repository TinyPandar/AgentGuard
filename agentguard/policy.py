"""Deterministic, task-scoped authorization policy."""

from __future__ import annotations

from fnmatch import fnmatchcase

from .models import (
    Artifact,
    Decision,
    DestinationZone,
    PolicyDecision,
    RiskLevel,
    Sensitivity,
    TaskGrant,
    ToolProposal,
)
from .registry import ToolSpec


class PolicyEngine:
    POLICY_ID = "agentguard-default-v0.1"

    def _decision(self, decision: Decision, reason: str) -> PolicyDecision:
        return PolicyDecision(decision, self.POLICY_ID, reason)

    @staticmethod
    def _resource_allowed(resource: str, patterns: frozenset[str]) -> bool:
        return any(fnmatchcase(resource, pattern) for pattern in patterns)

    @staticmethod
    def _data_flow_allowed(
        artifact: Artifact,
        destination: DestinationZone,
        grant: TaskGrant,
    ) -> bool:
        if destination is not DestinationZone.EXTERNAL:
            return True
        if artifact.sensitivity < Sensitivity.CONFIDENTIAL:
            return True
        flow = (artifact.sensitivity.name, destination.value)
        return flow in grant.allowed_data_flows

    def decide(
        self,
        *,
        grant: TaskGrant,
        proposal: ToolProposal,
        spec: ToolSpec,
        artifacts: tuple[Artifact, ...],
        context_risk: RiskLevel,
        calls_used: int,
    ) -> PolicyDecision:
        # Risk may tighten authority, but can never create authority.
        if grant.is_expired():
            return self._decision(Decision.DENY, "task grant has expired")
        if calls_used >= grant.max_tool_calls:
            return self._decision(Decision.DENY, "task tool-call budget exhausted")
        if spec.name not in grant.allowed_tools:
            return self._decision(
                Decision.DENY, "tool is outside the task-scoped grant"
            )
        if spec.permission and spec.permission not in grant.permissions:
            return self._decision(Decision.DENY, "required permission is missing")
        if spec.side_effect in grant.denied_side_effects:
            return self._decision(
                Decision.DENY, "tool side effect is explicitly denied"
            )
        if spec.resource_required and not proposal.resource:
            return self._decision(Decision.DENY, "tool resource is required")
        if proposal.resource and not self._resource_allowed(
            proposal.resource, grant.allowed_resources
        ):
            return self._decision(
                Decision.DENY, "resource is outside the task-scoped grant"
            )
        for artifact in artifacts:
            if not self._data_flow_allowed(artifact, spec.destination_zone, grant):
                return self._decision(
                    Decision.DENY,
                    f"{artifact.sensitivity.name} data cannot flow to "
                    f"{spec.destination_zone.value}",
                )
        if context_risk >= RiskLevel.HIGH and spec.risk_level >= RiskLevel.HIGH:
            return self._decision(
                Decision.DENY,
                "high-risk context cannot drive a high-risk tool",
            )
        if spec.require_confirmation:
            return self._decision(
                Decision.REQUIRE_CONFIRMATION,
                "high-risk tool requires backend confirmation",
            )
        return self._decision(Decision.ALLOW, "task grant and policy checks passed")
