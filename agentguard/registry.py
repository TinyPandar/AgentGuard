"""Tool metadata registry and mock execution surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .models import (
    DestinationZone,
    RiskLevel,
    SideEffect,
    ToolExecutionResult,
)

ToolHandler = Callable[[dict[str, Any], str], ToolExecutionResult]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    risk_level: RiskLevel
    permission: str
    side_effect: SideEffect
    destination_zone: DestinationZone
    argument_schema: dict[str, type]
    required_arguments: frozenset[str]
    handler: ToolHandler
    require_confirmation: bool = False
    resource_required: bool = False

    def validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        missing = self.required_arguments - arguments.keys()
        if missing:
            return f"missing required arguments: {sorted(missing)}"
        unknown = arguments.keys() - self.argument_schema.keys()
        if unknown:
            return f"unknown arguments: {sorted(unknown)}"
        for key, value in arguments.items():
            expected = self.argument_schema[key]
            if not isinstance(value, expected):
                return f"argument {key!r} must be {expected.__name__}"
        return None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def invoke_raw(
        self, name: str, arguments: dict[str, Any], trace_id: str
    ) -> ToolExecutionResult:
        """Unsafe baseline execution that intentionally bypasses policy."""

        spec = self.get(name)
        if spec is None:
            return ToolExecutionResult(
                executed=False,
                tool_name=name,
                error="unknown tool",
            )
        error = spec.validate_arguments(arguments)
        if error:
            return ToolExecutionResult(
                executed=False,
                tool_name=name,
                error=error,
            )
        return spec.handler(arguments, trace_id)
