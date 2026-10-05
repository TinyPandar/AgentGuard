"""Side-effect-safe tools for repeatable security experiments."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .models import (
    Artifact,
    Authority,
    DestinationZone,
    RiskLevel,
    Sensitivity,
    SideEffect,
    ToolExecutionResult,
    TrustLevel,
)
from .registry import ToolRegistry, ToolSpec


@dataclass
class MockToolEnvironment:
    external_messages: list[dict[str, str]] = field(default_factory=list)
    call_log: list[dict[str, object]] = field(default_factory=list)

    def registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(
            ToolSpec(
                name="search_public_docs",
                risk_level=RiskLevel.LOW,
                permission="public.search",
                side_effect=SideEffect.READ,
                destination_zone=DestinationZone.LOCAL,
                argument_schema={"query": str},
                required_arguments=frozenset({"query"}),
                handler=self.search_public_docs,
            )
        )
        registry.register(
            ToolSpec(
                name="query_internal_report",
                risk_level=RiskLevel.MEDIUM,
                permission="internal.report.read",
                side_effect=SideEffect.READ,
                destination_zone=DestinationZone.INTERNAL,
                argument_schema={"report_id": str},
                required_arguments=frozenset({"report_id"}),
                resource_required=True,
                handler=self.query_internal_report,
            )
        )
        registry.register(
            ToolSpec(
                name="send_external_message",
                risk_level=RiskLevel.HIGH,
                permission="external.send",
                side_effect=SideEffect.EXTERNAL_SEND,
                destination_zone=DestinationZone.EXTERNAL,
                argument_schema={"destination": str, "content": str},
                required_arguments=frozenset({"destination", "content"}),
                require_confirmation=True,
                handler=self.send_external_message,
            )
        )
        registry.register(
            ToolSpec(
                name="export_sensitive_data",
                risk_level=RiskLevel.CRITICAL,
                permission="sensitive.export",
                side_effect=SideEffect.READ,
                destination_zone=DestinationZone.INTERNAL,
                argument_schema={"dataset": str},
                required_arguments=frozenset({"dataset"}),
                resource_required=True,
                require_confirmation=True,
                handler=self.export_sensitive_data,
            )
        )
        return registry

    def _artifact(
        self,
        *,
        content: str,
        source_type: str,
        source_id: str,
        sensitivity: Sensitivity,
        taints: frozenset[str] = frozenset(),
    ) -> Artifact:
        return Artifact(
            artifact_id=f"artifact-{uuid.uuid4()}",
            content=content,
            source_type=source_type,
            source_id=source_id,
            trust_level=TrustLevel.INTERNAL,
            authority=Authority.DATA_ONLY,
            sensitivity=sensitivity,
            taint_labels=taints,
        )

    def search_public_docs(
        self, arguments: dict[str, object], trace_id: str
    ) -> ToolExecutionResult:
        self.call_log.append(
            {"trace_id": trace_id, "tool": "search_public_docs", **arguments}
        )
        artifact = self._artifact(
            content=f"Public search result for: {arguments['query']}",
            source_type="PUBLIC_SEARCH",
            source_id=str(arguments["query"]),
            sensitivity=Sensitivity.PUBLIC,
        )
        return ToolExecutionResult(
            executed=True,
            tool_name="search_public_docs",
            output=artifact.content,
            artifacts=(artifact,),
        )

    def query_internal_report(
        self, arguments: dict[str, object], trace_id: str
    ) -> ToolExecutionResult:
        report_id = str(arguments["report_id"])
        self.call_log.append(
            {"trace_id": trace_id, "tool": "query_internal_report", **arguments}
        )
        artifact = self._artifact(
            content=f"Internal report {report_id}: simulated confidential findings",
            source_type="INTERNAL_REPORT",
            source_id=report_id,
            sensitivity=Sensitivity.CONFIDENTIAL,
        )
        return ToolExecutionResult(
            executed=True,
            tool_name="query_internal_report",
            output=artifact.content,
            artifacts=(artifact,),
        )

    def send_external_message(
        self, arguments: dict[str, object], trace_id: str
    ) -> ToolExecutionResult:
        message = {
            "trace_id": trace_id,
            "destination": str(arguments["destination"]),
            "content": str(arguments["content"]),
        }
        self.external_messages.append(message)
        self.call_log.append(
            {"trace_id": trace_id, "tool": "send_external_message", **arguments}
        )
        return ToolExecutionResult(
            executed=True,
            tool_name="send_external_message",
            output={"status": "simulated_sent", "destination": message["destination"]},
        )

    def export_sensitive_data(
        self, arguments: dict[str, object], trace_id: str
    ) -> ToolExecutionResult:
        dataset = str(arguments["dataset"])
        self.call_log.append(
            {"trace_id": trace_id, "tool": "export_sensitive_data", **arguments}
        )
        artifact = self._artifact(
            content=f"Simulated secret rows from {dataset}",
            source_type="SENSITIVE_DATASET",
            source_id=dataset,
            sensitivity=Sensitivity.SECRET,
            taints=frozenset({"SENSITIVE_SOURCE"}),
        )
        return ToolExecutionResult(
            executed=True,
            tool_name="export_sensitive_data",
            output=artifact.content,
            artifacts=(artifact,),
        )
