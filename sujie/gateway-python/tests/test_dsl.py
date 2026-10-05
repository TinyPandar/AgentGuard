from pathlib import Path

import pytest
from sujie_gateway.dsl import PolicySyntaxError, evaluate, load_rules

POLICY = Path(__file__).resolve().parents[1] / "policies/m1.yaml"


def facts(kind="file.write", trust="LOCAL"):
    return {
        "runtime": {"prerequisites_passed": True},
        "action": {"effect": {"kind": kind, "destination_trust": trust}},
    }


def test_M1_DSL_001_allow_rule():
    assert evaluate(load_rules(POLICY.read_text("utf-8")), facts())[0] == "allow"


def test_M1_DSL_002_ask_overrides_allow():
    effect, matched = evaluate(
        load_rules(POLICY.read_text("utf-8")), facts("data.transfer", "UNTRUSTED_EXTERNAL")
    )
    assert effect == "ask"
    assert matched == ("allow_bounded_m1_action", "ask_external_transfer")


def test_M1_DSL_003_missing_fact_fails_closed():
    assert evaluate(load_rules(POLICY.read_text("utf-8")), {}) == ("block", ())


@pytest.mark.parametrize(
    "snippet", ["op: lt", "field: model.claim", "!!python/object:os.system []"]
)
def test_M1_DSL_004_rejects_unapproved_language(snippet):
    text = f"""schema_version: "0.1"
rules:
  - id: unsafe
    effect: allow
    when:
      - field: action.effect.kind
        {snippet}
        value: file.write
"""
    with pytest.raises(PolicySyntaxError):
        load_rules(text)


def test_M1_DSL_005_block_precedence():
    rules = load_rules("""schema_version: "0.1"
rules:
  - id: allowed
    effect: allow
    when: [{field: action.effect.kind, op: eq, value: file.write}]
  - id: stopped
    effect: hard_block
    when: [{field: action.effect.kind, op: eq, value: file.write}]
""")
    assert evaluate(rules, facts())[0] == "hard_block"
