import unittest
from datetime import datetime, timedelta, timezone

from agentguard.approval import ApprovalService
from agentguard.audit import AuditTrace
from agentguard.gateway import ToolGateway
from agentguard.mock_tools import MockToolEnvironment
from agentguard.models import (
    Artifact,
    Authority,
    Decision,
    RiskLevel,
    Sensitivity,
    TaskGrant,
    ToolProposal,
    TrustLevel,
)
from agentguard.policy import PolicyEngine


class GatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = MockToolEnvironment()
        self.approvals = ApprovalService()
        self.audit = AuditTrace()
        self.gateway = ToolGateway(
            registry=self.environment.registry(),
            policy=PolicyEngine(),
            approvals=self.approvals,
            audit=self.audit,
        )

    def grant(self, **overrides: object) -> TaskGrant:
        values = {
            "grant_id": "grant-test",
            "trace_id": "trace-test",
            "subject": "analyst-1",
            "objective": "send a public summary",
            "allowed_tools": frozenset({"send_external_message"}),
            "allowed_resources": frozenset({"external:partner.example"}),
            "permissions": frozenset({"external.send"}),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        values.update(overrides)
        return TaskGrant(**values)  # type: ignore[arg-type]

    def proposal(self, destination: str = "partner.example") -> ToolProposal:
        return ToolProposal(
            tool_name="send_external_message",
            arguments={"destination": destination, "content": "public summary"},
            resource=f"external:{destination}",
        )

    def test_tool_outside_task_grant_is_denied(self) -> None:
        proposal = ToolProposal(
            tool_name="export_sensitive_data",
            arguments={"dataset": "employees"},
            resource="dataset:employees",
        )
        result = self.gateway.execute(grant=self.grant(), proposal=proposal)
        self.assertFalse(result.executed)
        self.assertEqual(result.decision.decision, Decision.DENY)
        self.assertIn("outside the task-scoped grant", result.error)

    def test_confidential_external_flow_is_denied(self) -> None:
        artifact = Artifact(
            artifact_id="artifact-secret",
            content="confidential report",
            source_type="INTERNAL_REPORT",
            source_id="42",
            trust_level=TrustLevel.INTERNAL,
            authority=Authority.DATA_ONLY,
            sensitivity=Sensitivity.CONFIDENTIAL,
        )
        self.gateway.add_artifact(artifact)
        proposal = ToolProposal(
            tool_name="send_external_message",
            arguments={
                "destination": "partner.example",
                "content": artifact.content,
            },
            resource="external:partner.example",
            input_artifact_ids=(artifact.artifact_id,),
        )
        result = self.gateway.execute(grant=self.grant(), proposal=proposal)
        self.assertFalse(result.executed)
        self.assertIn("CONFIDENTIAL data cannot flow to EXTERNAL", result.error)

    def test_approval_is_argument_bound_and_one_time(self) -> None:
        proposal = self.proposal()
        first = self.gateway.execute(grant=self.grant(), proposal=proposal)
        self.assertFalse(first.executed)
        self.assertEqual(first.decision.decision, Decision.REQUIRE_CONFIRMATION)

        token = self.approvals.issue(
            trace_id="trace-test",
            subject="analyst-1",
            proposal=proposal,
        )
        changed = self.gateway.execute(
            grant=self.grant(),
            proposal=self.proposal("attacker.example"),
            approval_id=token.approval_id,
        )
        self.assertFalse(changed.executed)

        accepted = self.gateway.execute(
            grant=self.grant(),
            proposal=proposal,
            approval_id=token.approval_id,
        )
        self.assertTrue(accepted.executed)
        self.assertEqual(len(self.environment.external_messages), 1)

        replay = self.gateway.execute(
            grant=self.grant(),
            proposal=proposal,
            approval_id=token.approval_id,
        )
        self.assertFalse(replay.executed)
        self.assertIn("already been consumed", replay.error)

    def test_high_risk_context_can_only_tighten(self) -> None:
        result = self.gateway.execute(
            grant=self.grant(),
            proposal=self.proposal(),
            context_risk=RiskLevel.HIGH,
        )
        self.assertFalse(result.executed)
        self.assertIn("high-risk context", result.error)


if __name__ == "__main__":
    unittest.main()
