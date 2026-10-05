"""Shared, deterministic security data models.

The models intentionally contain no LLM calls. Authorization decisions are
made from explicit, inspectable fields rather than model self-assessment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any


class TrustLevel(str, Enum):
    UNTRUSTED = "UNTRUSTED"
    USER_CONTROLLED = "USER_CONTROLLED"
    INTERNAL = "INTERNAL"
    VERIFIED = "VERIFIED"
    SYSTEM = "SYSTEM"


class Authority(str, Enum):
    DATA_ONLY = "DATA_ONLY"
    USER_REQUEST = "USER_REQUEST"
    SYSTEM_POLICY = "SYSTEM_POLICY"


class Sensitivity(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    SECRET = 3


class RiskLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"


class Delivery(str, Enum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"


class SideEffect(str, Enum):
    NONE = "NONE"
    READ = "READ"
    WRITE = "WRITE"
    EXTERNAL_SEND = "EXTERNAL_SEND"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"


class DestinationZone(str, Enum):
    LOCAL = "LOCAL"
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


@dataclass(frozen=True)
class ScanResult:
    risk_score: float
    risk_level: RiskLevel
    attack_types: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    detector: str = "rule_detector"
    delivery: Delivery = Delivery.DIRECT
    source_type: str = "USER_INPUT"


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    content: str
    source_type: str
    source_id: str
    trust_level: TrustLevel
    authority: Authority
    sensitivity: Sensitivity
    taint_labels: frozenset[str] = frozenset()
    parent_artifact_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskGrant:
    """A task-scoped capability issued by trusted application code."""

    grant_id: str
    trace_id: str
    subject: str
    objective: str
    allowed_tools: frozenset[str]
    allowed_resources: frozenset[str]
    permissions: frozenset[str]
    allowed_data_flows: frozenset[tuple[str, str]] = frozenset()
    denied_side_effects: frozenset[SideEffect] = frozenset()
    max_tool_calls: int = 10
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return current >= expiry


@dataclass(frozen=True)
class ToolProposal:
    tool_name: str
    arguments: dict[str, Any]
    resource: str | None = None
    input_artifact_ids: tuple[str, ...] = ()


@dataclass
class ApprovalToken:
    approval_id: str
    trace_id: str
    subject: str
    tool_name: str
    arguments_hash: str
    expires_at: datetime
    nonce: str
    one_time: bool = True
    consumed: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    policy_id: str
    reason: str


@dataclass(frozen=True)
class AuditEvent:
    trace_id: str
    event_type: str
    timestamp: datetime
    details: dict[str, Any]


@dataclass(frozen=True)
class ToolExecutionResult:
    executed: bool
    tool_name: str
    output: Any = None
    artifacts: tuple[Artifact, ...] = ()
    decision: PolicyDecision | None = None
    error: str | None = None
