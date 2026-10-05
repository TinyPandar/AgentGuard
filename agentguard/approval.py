"""Backend-owned, argument-bound approval tokens."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from .models import ApprovalToken, ToolProposal


def proposal_digest(proposal: ToolProposal) -> str:
    payload = {
        "tool_name": proposal.tool_name,
        "arguments": proposal.arguments,
        "resource": proposal.resource,
        "input_artifact_ids": list(proposal.input_artifact_ids),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class ApprovalService:
    """Issues approvals only after a trusted UI/backend confirmation event."""

    def __init__(self) -> None:
        self._tokens: dict[str, ApprovalToken] = {}

    def issue(
        self,
        *,
        trace_id: str,
        subject: str,
        proposal: ToolProposal,
        ttl_seconds: int = 300,
    ) -> ApprovalToken:
        token = ApprovalToken(
            approval_id=f"approval-{uuid.uuid4()}",
            trace_id=trace_id,
            subject=subject,
            tool_name=proposal.tool_name,
            arguments_hash=proposal_digest(proposal),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            nonce=secrets.token_urlsafe(18),
        )
        self._tokens[token.approval_id] = token
        return token

    def validate_and_consume(
        self,
        approval_id: str | None,
        *,
        trace_id: str,
        subject: str,
        proposal: ToolProposal,
    ) -> tuple[bool, str]:
        if not approval_id:
            return False, "backend approval is required"
        token = self._tokens.get(approval_id)
        if token is None:
            return False, "approval does not exist"
        if token.consumed:
            return False, "approval has already been consumed"
        if datetime.now(timezone.utc) >= token.expires_at:
            return False, "approval has expired"
        if token.trace_id != trace_id or token.subject != subject:
            return False, "approval is bound to another task or subject"
        if token.tool_name != proposal.tool_name:
            return False, "approval is bound to another tool"
        if token.arguments_hash != proposal_digest(proposal):
            return False, "tool arguments changed after approval"
        if token.one_time:
            token.consumed = True
        return True, "approval is valid"
