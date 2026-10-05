"""Schema-first, immutable JSON domain documents; no database or network access."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry
from rfc3986_validator import validate_rfc3986

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
SCHEMA_NAMES = (
    "task-contract",
    "task-grant",
    "provenance-envelope",
    "semantic-action",
    "decision-record",
    "approval-record",
    "trace-event",
    "security-exception",
    "detection-finding",
)
ID_PATTERN = re.compile(
    r"(?:[0-7][0-9A-HJKMNP-TV-Z]{25}|"
    r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})\Z"
)
FORMATS = FormatChecker()


class ContractError(ValueError):
    """Safe failure code; never reflect untrusted field values into exceptions."""


@FORMATS.checks("sujie-id")
def valid_id(value: Any) -> bool:
    return not isinstance(value, str) or ID_PATTERN.fullmatch(value) is not None


@FORMATS.checks("uri")
def valid_uri(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    return not any(c.isspace() or ord(c) < 32 for c in value) and bool(
        validate_rfc3986(value, rule="URI")
    )


@FORMATS.checks("date-time")
def valid_utc(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    try:
        return (
            value.endswith("Z") and datetime.fromisoformat(value).utcoffset().total_seconds() == 0
        )
    except (ValueError, AttributeError):
        return False


def local_scope(value: str) -> tuple[str, bool] | None:
    """Only canonical POSIX literals and trailing /**. No filesystem claim."""
    recursive = value.endswith("/**")
    base = value[:-3] if recursive else value
    if not base.startswith("/") or base.startswith("//"):
        return None
    if any(c in value for c in ("\\", "%", "?", "#", "\x00")):
        return None
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return None
    if any(c in base for c in ("*", "[", "]", "{", "}")):
        return None
    if base != "/" and any(part in ("", ".", "..") for part in base[1:].split("/")):
        return None
    return base, recursive


@FORMATS.checks("resource-scope")
def valid_scope(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    if value.startswith("/"):
        return local_scope(value) is not None
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment
            and "*" not in value
            and not any(c.isspace() or ord(c) < 32 for c in value)
            and parsed.port != 0
        )
    except ValueError:
        return False


def _reject_constant(_: str) -> None:
    raise ContractError("NON_FINITE_JSON")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def load_json(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        raise ContractError("INVALID_JSON") from None


def _check_json(value: Any) -> None:
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _check_json(item)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            _check_json(item)
        return
    raise ContractError("NON_JSON_VALUE")


def canonical_json(value: Any) -> str:
    _check_json(value)
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def snapshot_hash(value: Any) -> str:
    """Python M0 snapshot fingerprint, not a signature or cross-language JCS claim."""
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@lru_cache(maxsize=9)
def validator(name: str) -> Draft202012Validator:
    if name not in SCHEMA_NAMES:
        raise ContractError("UNKNOWN_SCHEMA")
    schema = load_json((CONTRACTS / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    # All references are local $defs; Registry has no network retriever.
    return Draft202012Validator(schema, format_checker=FORMATS, registry=Registry())


def validate_document(name: str, value: Any) -> None:
    _check_json(value)
    if next(validator(name).iter_errors(value), None) is not None:
        raise ContractError("SCHEMA_REJECTED")


@dataclass(frozen=True, slots=True, init=False, repr=False)
class DomainDocument:
    """A validated immutable snapshot. to_dict returns a defensive copy."""

    _json: str
    schema_name: ClassVar[str]

    def __init__(self, payload: dict[str, Any]):
        validate_document(self.schema_name, payload)
        object.__setattr__(self, "_json", canonical_json(payload))

    def to_dict(self) -> dict[str, Any]:
        return load_json(self._json)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(validated_snapshot)"


class TaskContract(DomainDocument):
    schema_name = "task-contract"


class TaskGrant(DomainDocument):
    schema_name = "task-grant"


class ProvenanceEnvelope(DomainDocument):
    schema_name = "provenance-envelope"


class SemanticAction(DomainDocument):
    schema_name = "semantic-action"


class DecisionRecord(DomainDocument):
    schema_name = "decision-record"


class ApprovalRecord(DomainDocument):
    schema_name = "approval-record"


class TraceEvent(DomainDocument):
    schema_name = "trace-event"


class SecurityException(DomainDocument):
    schema_name = "security-exception"


class DetectionFinding(DomainDocument):
    schema_name = "detection-finding"


DOCUMENT_TYPES = {
    cls.schema_name: cls
    for cls in (
        TaskContract,
        TaskGrant,
        ProvenanceEnvelope,
        SemanticAction,
        DecisionRecord,
        ApprovalRecord,
        TraceEvent,
        SecurityException,
        DetectionFinding,
    )
}
