"""Append-only audit trace used by demos, tests, and future adapters."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .models import AuditEvent


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_value(v) for v in value]
    return value


class AuditTrace:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.events: list[AuditEvent] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, trace_id: str, event_type: str, **details: Any) -> AuditEvent:
        event = AuditEvent(
            trace_id=trace_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            details=details,
        )
        self.events.append(event)
        if self.path:
            payload = _json_value(asdict(event))
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
                )
        return event

    def for_trace(self, trace_id: str) -> list[AuditEvent]:
        return [event for event in self.events if event.trace_id == trace_id]
