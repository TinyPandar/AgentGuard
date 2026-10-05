"""Pure M0 architecture guards. These do not authenticate callers or execute tools."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .contracts import (
    ApprovalRecord,
    ContractError,
    DecisionRecord,
    ProvenanceEnvelope,
    SemanticAction,
    TaskContract,
    TaskGrant,
    local_scope,
    snapshot_hash,
)

AUTHORITY = {"DATA_ONLY": 0, "USER_REQUEST": 1, "CONTROL_PLANE": 2}
INTEGRITY = {"UNTRUSTED": 0, "VALIDATED": 1, "TRUSTED": 2}
CONFIDENTIALITY = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "SECRET": 3}
DECISION = {"ALLOW": 0, "ASK": 1, "BLOCK": 2}


class InvariantViolation(ContractError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise InvariantViolation(code)


def check_clock(now: datetime) -> None:
    require(now.tzinfo is not None and now.utcoffset() == timedelta(0), "UTC_CLOCK_REQUIRED")


def scope_within(child: str, parent: str) -> bool:
    """Conservative lexical containment, not glob matching or filesystem resolution."""
    if child == parent:
        return True
    c, p = local_scope(child), local_scope(parent)
    if c is None or p is None or not p[1]:
        return False
    return c[0] == p[0] or c[0].startswith(p[0].rstrip("/") + "/")


def assert_child_within_parent(parent: TaskGrant, child: TaskGrant, *, now: datetime) -> None:
    """Checks the parent ceiling only. Need/Contract intersection is a separate M1 gate."""
    check_clock(now)
    p, c = parent.to_dict(), child.to_dict()
    require(p["status"] == c["status"] == "ACTIVE", "GRANT_NOT_ACTIVE")
    require(c["parent_grant_id"] == p["grant_id"], "WRONG_PARENT")
    require(c["grant_id"] != p["grant_id"], "GRANT_SELF_PARENT")
    require(
        now < datetime.fromisoformat(c["expires_at"]) <= datetime.fromisoformat(p["expires_at"]),
        "GRANT_EXPIRY_EXPANDED",
    )
    require(set(c["effects"]) <= set(p["effects"]), "GRANT_EFFECT_EXPANDED")
    require(
        all(any(scope_within(s, t) for t in p["resource_scopes"]) for s in c["resource_scopes"]),
        "GRANT_RESOURCE_EXPANDED",
    )
    require(set(c["budgets"]) <= set(p["budgets"]), "GRANT_BUDGET_DIMENSION_EXPANDED")
    require(all(n <= p["budgets"][k] for k, n in c["budgets"].items()), "GRANT_BUDGET_EXPANDED")


def assert_use(envelope: ProvenanceEnvelope, purpose: str) -> None:
    p = envelope.to_dict()
    require(purpose in p["allowed_uses"] and purpose not in p["forbidden_uses"], "USE_NOT_ALLOWED")
    require(
        not (p["authority"] == "DATA_ONLY" and purpose in {"AUTHORIZE", "CHANGE_POLICY"}),
        "DATA_CANNOT_AUTHORIZE",
    )


def assert_ordinary_derivation(
    parents: list[ProvenanceEnvelope], child: ProvenanceEnvelope
) -> None:
    """Validate a claimed derivation; does not yet build the M2 provenance/exposure store."""
    require(bool(parents), "MISSING_PARENTS")
    inputs, output = [p.to_dict() for p in parents], child.to_dict()
    ids = {p["artifact_id"] for p in inputs}
    require(len(ids) == len(inputs), "DUPLICATE_PARENT")
    require(set(output["parents"]) == ids, "PARENT_SET_MISMATCH")
    require(output["artifact_id"] not in ids, "ARTIFACT_SELF_PARENT")
    require(
        AUTHORITY[output["authority"]] <= min(AUTHORITY[p["authority"]] for p in inputs),
        "AUTHORITY_UPGRADE",
    )
    require(
        INTEGRITY[output["integrity"]] <= min(INTEGRITY[p["integrity"]] for p in inputs),
        "INTEGRITY_UPGRADE",
    )
    require(
        CONFIDENTIALITY[output["confidentiality"]]
        >= max(CONFIDENTIALITY[p["confidentiality"]] for p in inputs),
        "CONFIDENTIALITY_DOWNGRADE",
    )
    allowed = set.intersection(*(set(p["allowed_uses"]) for p in inputs))
    forbidden = set.union(*(set(p["forbidden_uses"]) for p in inputs))
    require(set(output["allowed_uses"]) <= allowed, "USES_EXPANDED")
    require(set(output["forbidden_uses"]) >= forbidden, "FORBIDDEN_USES_LOST")
    require(not set(output["allowed_uses"]) & set(output["forbidden_uses"]), "USE_CONFLICT")
    if output["authority"] == "DATA_ONLY":
        require(
            not {"AUTHORIZE", "CHANGE_POLICY"} & set(output["allowed_uses"]),
            "DATA_CANNOT_AUTHORIZE",
        )
    for span in output["source_spans"]:
        require(
            span["source_start"] <= span["source_end"] and span["view_start"] <= span["view_end"],
            "INVALID_SPAN",
        )
    for transform in output["transformations"]:
        if transform["type"] in {"SUMMARY", "MODEL_REWRITE"}:
            require(
                transform["mapping_ref"] is None and not output["source_spans"],
                "GENERATED_TEXT_HAS_NO_EXACT_CAUSAL_MAP",
            )
    require(
        all(
            datetime.fromisoformat(output["created_at"]) >= datetime.fromisoformat(p["created_at"])
            for p in inputs
        ),
        "DERIVATION_PREDATES_PARENT",
    )


def tighten_decision(current: str, recommendation: str) -> str:
    """Semantic advice may only tighten an already determined policy outcome."""
    require(current in DECISION and recommendation in DECISION, "UNKNOWN_DECISION")
    return max((current, recommendation), key=DECISION.__getitem__)


def make_binding(
    action: SemanticAction,
    contract: TaskContract,
    grant: TaskGrant,
    *,
    input_content_hash: str,
    provenance_snapshot_hash: str,
) -> dict[str, Any]:
    """Trusted-host snapshots only; no authentication, capability grant or signing here."""
    a, c, g = action.to_dict(), contract.to_dict(), grant.to_dict()
    require(a["contract_id"] == c["contract_id"] == g["contract_id"], "CONTRACT_MISMATCH")
    require(a["grant_id"] == g["grant_id"], "GRANT_MISMATCH")
    require(a["subject_id"] == g["subject_id"], "SUBJECT_MISMATCH")
    return {
        "principal_id": c["principal_id"],
        "session_id": c["session_id"],
        "subject_id": a["subject_id"],
        "action_id": a["action_id"],
        "action_hash": snapshot_hash(a),
        "contract_id": c["contract_id"],
        "contract_version": c["version"],
        "contract_snapshot_hash": snapshot_hash(c),
        "grant_id": g["grant_id"],
        "grant_snapshot_hash": snapshot_hash(g),
        "policy_snapshot_hash": c["policy_snapshot_hash"],
        "tool_identity": a["tool_identity"],
        "materialized_args_hash": a["materialized_args_hash"],
        "input_content_hash": input_content_hash,
        "provenance_snapshot_hash": provenance_snapshot_hash,
    }


def approval_is_valid(
    approval: ApprovalRecord,
    decision: DecisionRecord,
    action: SemanticAction,
    contract: TaskContract,
    grant: TaskGrant,
    *,
    now: datetime,
    input_content_hash: str,
    provenance_snapshot_hash: str,
) -> bool:
    """Pure eligibility predicate, NOT the future atomic consume/commit implementation."""
    check_clock(now)
    ap, d, a, c, g = (x.to_dict() for x in (approval, decision, action, contract, grant))
    if d["decision"] != "ASK" or d["hard_block"]:
        return False
    if ap["status"] != "APPROVED" or ap["consumed"] or ap["approved_at"] is None:
        return False
    if c["status"] != "ACTIVE" or g["status"] != "ACTIVE":
        return False
    if not (
        datetime.fromisoformat(ap["created_at"])
        <= datetime.fromisoformat(ap["approved_at"])
        <= now
        < min(datetime.fromisoformat(x["expires_at"]) for x in (ap, c, g))
    ):
        return False
    if not (
        ap["decision_id"] == d["decision_id"]
        and ap["approved_by"] == c["principal_id"]
        and d["action_id"] == a["action_id"]
        and d["contract_id"] == c["contract_id"]
        and d["grant_id"] == g["grant_id"]
        and d["policy_snapshot_hash"] == c["policy_snapshot_hash"]
    ):
        return False
    try:
        binding = make_binding(
            action,
            contract,
            grant,
            input_content_hash=input_content_hash,
            provenance_snapshot_hash=provenance_snapshot_hash,
        )
    except InvariantViolation:
        return False
    return ap["binding"] == binding
