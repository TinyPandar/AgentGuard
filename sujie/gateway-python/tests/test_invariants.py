import copy
from datetime import timedelta

import pytest
from sujie_gateway.contracts import (
    ApprovalRecord,
    ContractError,
    DecisionRecord,
    ProvenanceEnvelope,
    SemanticAction,
    TaskContract,
    TaskGrant,
)
from sujie_gateway.invariants import (
    InvariantViolation,
    approval_is_valid,
    assert_child_within_parent,
    assert_ordinary_derivation,
    assert_use,
    make_binding,
    tighten_decision,
)

NEW_ID = "01K4M0AAAAAAAAAAAAAAA00090"
NEW_HASH = "sha256:" + "9" * 64


@pytest.fixture
def child_pair(fixture_document):
    parent = fixture_document("task-grant")
    child = copy.deepcopy(parent)
    child.update(
        grant_id=NEW_ID,
        parent_grant_id=parent["grant_id"],
        subject_id="01K4M0AAAAAAAAAAAAAAA00091",
        effects=["file.read"],
        resource_scopes=["/workspace/case-001/reports/**"],
        budgets={"tool_calls": 5},
        expires_at="2026-09-05T10:30:00Z",
    )
    return parent, child


def test_ARCH_GRANT_001_legal_attenuation(child_pair, now):
    p, c = child_pair
    assert_child_within_parent(TaskGrant(p), TaskGrant(c), now=now)


@pytest.mark.parametrize(
    "field,value",
    [
        ("effects", ["file.read", "git.push"]),
        ("resource_scopes", ["/workspace/case-002/**"]),
        ("resource_scopes", ["/workspace/case-001-lookalike/**"]),
        ("resource_scopes", ["/workspace/**"]),
        ("budgets", {"tool_calls": 21}),
        ("budgets", {"tool_calls": 2, "network_calls": 1}),
        ("expires_at", "2026-09-05T12:00:00Z"),
        ("expires_at", "2026-09-05T09:00:00Z"),
        ("parent_grant_id", None),
        ("status", "REVOKED"),
    ],
    ids=[f"ARCH-GRANT-{i:03d}" for i in range(2, 12)],
)
def test_grant_escalation_rejected(child_pair, field, value, now):
    p, c = child_pair
    c[field] = value
    with pytest.raises(InvariantViolation):
        assert_child_within_parent(TaskGrant(p), TaskGrant(c), now=now)


def test_ARCH_GRANT_012_revoked_parent(child_pair, now):
    p, c = child_pair
    p["status"] = "REVOKED"
    with pytest.raises(InvariantViolation):
        assert_child_within_parent(TaskGrant(p), TaskGrant(c), now=now)


def test_ARCH_GRANT_013_self_parent(child_pair, now):
    p, c = child_pair
    c["grant_id"] = p["grant_id"]
    with pytest.raises(InvariantViolation):
        assert_child_within_parent(TaskGrant(p), TaskGrant(c), now=now)


def test_ARCH_GRANT_014_literal_scope_does_not_grant_subtree(child_pair, now):
    p, c = child_pair
    p["resource_scopes"] = ["/workspace/case-001"]
    with pytest.raises(InvariantViolation):
        assert_child_within_parent(TaskGrant(p), TaskGrant(c), now=now)


def test_ARCH_GRANT_015_reject_naive_clock(child_pair, now):
    p, c = child_pair
    with pytest.raises(InvariantViolation):
        assert_child_within_parent(TaskGrant(p), TaskGrant(c), now=now.replace(tzinfo=None))


@pytest.fixture
def derivation(fixture_document):
    parent = fixture_document("provenance-envelope")
    parent["confidentiality"] = "SECRET"
    child = copy.deepcopy(parent)
    child.update(
        artifact_id=NEW_ID,
        parents=[parent["artifact_id"]],
        content_ref="evidence://fixture/derived",
        content_hash=NEW_HASH,
        transformations=[{"type": "SUMMARY", "version": "1", "mapping_ref": None}],
        source_spans=[],
    )
    return parent, child


def test_ARCH_PROV_001_safe_derivation(derivation):
    p, c = derivation
    assert_ordinary_derivation([ProvenanceEnvelope(p)], ProvenanceEnvelope(c))


@pytest.mark.parametrize(
    "field,value",
    [
        ("authority", "USER_REQUEST"),
        ("integrity", "TRUSTED"),
        ("confidentiality", "PUBLIC"),
        ("parents", []),
        ("parents", ["01K4M0AAAAAAAAAAAAAAA00091"]),
        ("allowed_uses", ["READ", "AUTHORIZE"]),
        ("forbidden_uses", []),
        ("source_spans", [{"source_start": 0, "source_end": 2, "view_start": 0, "view_end": 2}]),
        ("created_at", "2026-09-05T08:00:00Z"),
    ],
    ids=[f"ARCH-PROV-{i:03d}" for i in range(2, 11)],
)
def test_provenance_cannot_be_laundered(derivation, field, value):
    p, c = derivation
    c[field] = value
    with pytest.raises(InvariantViolation):
        assert_ordinary_derivation([ProvenanceEnvelope(p)], ProvenanceEnvelope(c))


def test_ARCH_PROV_011_data_only_cannot_authorize_even_with_forged_use(fixture_document):
    p = fixture_document("provenance-envelope")
    p["allowed_uses"].append("AUTHORIZE")
    p["forbidden_uses"].remove("AUTHORIZE")
    with pytest.raises(InvariantViolation):
        assert_use(ProvenanceEnvelope(p), "AUTHORIZE")


@pytest.mark.parametrize("purpose", ["READ", "ANALYZE", "QUOTE", "STORE_EVIDENCE"])
def test_ARCH_PROV_012_dangerous_evidence_remains_usable(fixture_document, purpose):
    assert_use(ProvenanceEnvelope(fixture_document("provenance-envelope")), purpose)


def test_ARCH_PROV_013_mixed_sources_use_most_restrictive(derivation):
    p, c = derivation
    second = copy.deepcopy(p)
    second.update(
        artifact_id="01K4M0AAAAAAAAAAAAAAA00091", confidentiality="PUBLIC", allowed_uses=["READ"]
    )
    c["parents"].append(second["artifact_id"])
    c["allowed_uses"] = ["READ"]
    assert_ordinary_derivation(
        [ProvenanceEnvelope(p), ProvenanceEnvelope(second)], ProvenanceEnvelope(c)
    )
    c["allowed_uses"].append("ANALYZE")
    with pytest.raises(InvariantViolation):
        assert_ordinary_derivation(
            [ProvenanceEnvelope(p), ProvenanceEnvelope(second)], ProvenanceEnvelope(c)
        )


def test_ARCH_PROV_014_summary_mapping_cannot_claim_exact_causality(derivation):
    p, c = derivation
    c["transformations"][0]["mapping_ref"] = "evidence://fake/exact"
    with pytest.raises(InvariantViolation):
        assert_ordinary_derivation([ProvenanceEnvelope(p)], ProvenanceEnvelope(c))


@pytest.mark.parametrize("recommendation", ["ALLOW", "ASK", "BLOCK"])
def test_ARCH_DECISION_001_semantic_model_cannot_relax_block(recommendation):
    assert tighten_decision("BLOCK", recommendation) == "BLOCK"


def test_ARCH_DECISION_002_semantic_advice_can_tighten():
    assert tighten_decision("ALLOW", "ASK") == "ASK"
    assert tighten_decision("ASK", "BLOCK") == "BLOCK"
    assert tighten_decision("ASK", "ALLOW") == "ASK"


@pytest.fixture
def approval_case(fixture_document):
    data = {
        name: fixture_document(name)
        for name in (
            "approval-record",
            "decision-record",
            "semantic-action",
            "task-contract",
            "task-grant",
        )
    }
    kwargs = {
        "input_content_hash": "sha256:" + "c" * 64,
        "provenance_snapshot_hash": "sha256:" + "1" * 64,
    }
    data["approval-record"]["binding"] = make_binding(
        SemanticAction(data["semantic-action"]),
        TaskContract(data["task-contract"]),
        TaskGrant(data["task-grant"]),
        **kwargs,
    )
    return data, kwargs


def approved(case, now):
    data, kwargs = case
    return approval_is_valid(
        ApprovalRecord(data["approval-record"]),
        DecisionRecord(data["decision-record"]),
        SemanticAction(data["semantic-action"]),
        TaskContract(data["task-contract"]),
        TaskGrant(data["task-grant"]),
        now=now,
        **kwargs,
    )


def test_ARCH_APPROVAL_001_valid_confirmation(approval_case, now):
    assert approved(approval_case, now)


@pytest.mark.parametrize("hard", [False, True], ids=["ordinary-block", "hard-block"])
def test_ARCH_APPROVAL_002_block_cannot_be_approved(approval_case, now, hard):
    data, _ = approval_case
    data["decision-record"].update(decision="BLOCK", hard_block=hard)
    assert not approved(approval_case, now)


@pytest.mark.parametrize(
    "name,path,value",
    [
        ("semantic-action", ["materialized_args_hash"], NEW_HASH),
        ("semantic-action", ["tool_identity", "tool_version_hash"], NEW_HASH),
        ("semantic-action", ["tool_identity", "tool_name"], "send_report"),
        ("semantic-action", ["tool_identity", "server_id"], NEW_ID),
        ("semantic-action", ["effect", "resources"], ["https://receiver.invalid/upload"]),
        ("semantic-action", ["input_artifacts"], [NEW_ID]),
        ("semantic-action", ["subject_id"], NEW_ID),
        ("semantic-action", ["action_id"], NEW_ID),
        ("task-contract", ["version"], 2),
        ("task-contract", ["policy_snapshot_hash"], NEW_HASH),
        ("task-contract", ["session_id"], NEW_ID),
        ("task-contract", ["status"], "REVOKED"),
        ("task-grant", ["status"], "REVOKED"),
        ("task-grant", ["budgets", "tool_calls"], 0),
        ("approval-record", ["consumed"], True),
        ("approval-record", ["status"], "PENDING"),
        ("approval-record", ["approved_by"], NEW_ID),
        ("approval-record", ["decision_id"], NEW_ID),
        ("approval-record", ["approved_at"], "2026-09-05T09:59:00Z"),
        ("decision-record", ["action_id"], NEW_ID),
    ],
    ids=[f"ARCH-APPROVAL-{i:03d}" for i in range(3, 23)],
)
def test_approval_binding_drift(approval_case, now, name, path, value):
    data, _ = approval_case
    target = data[name]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert not approved(approval_case, now)


@pytest.mark.parametrize("key", ["input_content_hash", "provenance_snapshot_hash"])
def test_ARCH_APPROVAL_023_input_state_drift(approval_case, now, key):
    _, kwargs = approval_case
    kwargs[key] = NEW_HASH
    assert not approved(approval_case, now)


def test_ARCH_APPROVAL_024_expired(approval_case, now):
    assert not approved(approval_case, now + timedelta(minutes=15))


def test_ARCH_MODEL_001_input_mutation_cannot_change_snapshot(fixture_document):
    payload = fixture_document("task-grant")
    grant = TaskGrant(payload)
    payload["effects"].append("git.push")
    exported = grant.to_dict()
    exported["effects"].append("exec")
    assert grant.to_dict()["effects"] == ["file.read", "file.write:report"]
    with pytest.raises((AttributeError, TypeError)):
        grant._json = "{}"


def test_ARCH_MODEL_002_error_does_not_echo_secret(fixture_document):
    payload = fixture_document("task-grant")
    payload["SYNTHETIC_SECRET_DO_NOT_ECHO"] = True
    with pytest.raises(ContractError) as caught:
        TaskGrant(payload)
    assert "SYNTHETIC_SECRET" not in str(caught.value)
