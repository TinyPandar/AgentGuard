"""M1 Agent-container check: only Gateway is reachable; no tool credentials or mounts."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import urllib.request
from pathlib import Path

from sujie_demo_agent.graph import DeterministicDecisionModel, build_agent


class HttpGateway:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def call(self, tool: str, args: dict) -> dict:
        return await asyncio.to_thread(self._call, tool, args)

    def _call(self, tool: str, args: dict) -> dict:
        body = json.dumps({"tool": tool, "arguments": args}).encode()
        request = urllib.request.Request(
            self.base_url + "/v1/calls",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)


def tcp_is_unreachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return False
    except OSError:
        return True


async def main() -> int:
    gateway = HttpGateway(os.environ.get("SUJIE_GATEWAY_URL", "http://gateway:8000"))
    clean = await build_agent(gateway, DeterministicDecisionModel()).ainvoke({"alert_id": "clean"})
    injected = await build_agent(gateway, DeterministicDecisionModel()).ainvoke(
        {"alert_id": "injected"}
    )
    summary = {
        "clean_completed": clean["completed"],
        "injected_completed": injected["completed"],
        "injected_decisions": [item["decision"] for item in injected["decisions"]],
        "receiver_directly_unreachable": tcp_is_unreachable("receiver", 8080),
        "external_network_unreachable": tcp_is_unreachable("1.1.1.1", 443),
        "secret_mount_absent": not Path("/var/lib/sujie/workspace/case-001/secret.txt").exists(),
        "docker_socket_absent": not Path("/var/run/docker.sock").exists(),
        "model_kind": "deterministic-test-model-not-llm",
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return (
        0
        if summary
        == {
            "clean_completed": True,
            "injected_completed": True,
            "injected_decisions": ["ALLOW", "BLOCK", "BLOCK", "ALLOW"],
            "receiver_directly_unreachable": True,
            "external_network_unreachable": True,
            "secret_mount_absent": True,
            "docker_socket_absent": True,
            "model_kind": "deterministic-test-model-not-llm",
        }
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
