"""Small typed policy DSL. Parsing is data-only; no eval or dynamic imports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from .invariants import scope_within

OPS = {
    "eq",
    "neq",
    "in",
    "not_in",
    "matches",
    "path_within",
    "gte",
    "lte",
    "contains_any",
    "exists",
}
EFFECTS = {"allow": 0, "ask": 1, "block": 2, "hard_block": 3}
NAMESPACES = {
    "principal",
    "contract",
    "grant",
    "action",
    "data",
    "provenance",
    "tool",
    "runtime",
    "history",
}


class PolicySyntaxError(ValueError):
    pass


def field_value(facts: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = facts
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


@dataclass(frozen=True)
class Predicate:
    field: str
    op: str
    value: Any = None

    def matches(self, facts: dict[str, Any]) -> bool:
        present, actual = field_value(facts, self.field)
        if self.op == "exists":
            return present is bool(self.value)
        if not present:
            return False
        if self.op == "eq":
            return actual == self.value
        if self.op == "neq":
            return actual != self.value
        if self.op == "in":
            return isinstance(self.value, list) and actual in self.value
        if self.op == "not_in":
            return isinstance(self.value, list) and actual not in self.value
        if self.op == "contains_any":
            return (
                isinstance(actual, list)
                and isinstance(self.value, list)
                and bool(set(actual) & set(self.value))
            )
        if self.op == "path_within":
            return (
                isinstance(actual, str)
                and isinstance(self.value, str)
                and scope_within(actual, self.value)
            )
        if self.op in {"gte", "lte"}:
            return (
                type(actual) in (int, float)
                and type(self.value) in (int, float)
                and (actual >= self.value if self.op == "gte" else actual <= self.value)
            )
        if self.op == "matches":
            return (
                isinstance(actual, str)
                and isinstance(self.value, str)
                and len(self.value) <= 256
                and re.fullmatch(self.value, actual) is not None
            )
        raise PolicySyntaxError("UNKNOWN_OPERATOR")


@dataclass(frozen=True)
class Rule:
    rule_id: str
    effect: str
    predicates: tuple[Predicate, ...]

    def matches(self, facts: dict[str, Any]) -> bool:
        return all(item.matches(facts) for item in self.predicates)


def load_rules(text: str) -> tuple[Rule, ...]:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError:
        raise PolicySyntaxError("INVALID_YAML") from None
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "rules"}:
        raise PolicySyntaxError("INVALID_POLICY_ROOT")
    if raw["schema_version"] != "0.1" or not isinstance(raw["rules"], list):
        raise PolicySyntaxError("UNSUPPORTED_POLICY_VERSION")
    rules = []
    ids = set()
    for item in raw["rules"]:
        if not isinstance(item, dict) or set(item) != {"id", "effect", "when"}:
            raise PolicySyntaxError("INVALID_RULE")
        if not isinstance(item["id"], str) or not item["id"] or item["id"] in ids:
            raise PolicySyntaxError("INVALID_RULE_ID")
        ids.add(item["id"])
        if item["effect"] not in EFFECTS or not isinstance(item["when"], list) or not item["when"]:
            raise PolicySyntaxError("INVALID_RULE_BODY")
        predicates = []
        for raw_predicate in item["when"]:
            if not isinstance(raw_predicate, dict) or set(raw_predicate) - {"field", "op", "value"}:
                raise PolicySyntaxError("INVALID_PREDICATE")
            field, op = raw_predicate.get("field"), raw_predicate.get("op")
            if not isinstance(field, str) or field.split(".", 1)[0] not in NAMESPACES:
                raise PolicySyntaxError("INVALID_FACT_NAMESPACE")
            if op not in OPS or (op != "exists" and "value" not in raw_predicate):
                raise PolicySyntaxError("INVALID_OPERATOR")
            predicates.append(Predicate(field, op, raw_predicate.get("value")))
        rules.append(Rule(item["id"], item["effect"], tuple(predicates)))
    return tuple(rules)


def evaluate(rules: tuple[Rule, ...], facts: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    matched = tuple(rule for rule in rules if rule.matches(facts))
    if not matched:
        return "block", ()
    strictest = max(matched, key=lambda rule: EFFECTS[rule.effect]).effect
    return strictest, tuple(rule.rule_id for rule in matched)
