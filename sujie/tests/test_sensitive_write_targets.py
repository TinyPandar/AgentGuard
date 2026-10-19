"""能力3 fs.write: sensitive targets stay blocked even under a widened trusted grant."""

import sys

import pytest
from mcp import StdioServerParameters
from receiver import Receiver
from sujie_gateway.contracts import TaskContract, TaskGrant
from sujie_gateway.m1_runtime import M1Gateway, StdioMCPProxy
from sujie_gateway.sensitive_targets import sensitive_write_target
from test_m1_e2e import OPERATIONS_SERVER, make_contracts

SENSITIVE = [
    "case-001/.ssh/authorized_keys",
    "case-001/.vscode/settings.json",  # CVE-2025-53773: IDE agent auto-approve setting
    "case-001/.git/hooks/pre-commit",
    "case-001/.github/workflows/ci.yml",
    "case-001/.env",
    "case-001/.bashrc",
    "case-001/keys/server.pem",
]
ORDINARY = ["case-001/output/report.txt", "case-001/notes/ssh_hardening.md", "case-001/env.txt"]


@pytest.mark.parametrize(
    "path,expected", [(p, True) for p in SENSITIVE] + [(p, False) for p in ORDINARY]
)
def test_sensitive_name_matcher(path, expected):
    assert sensitive_write_target("/workspace/" + path) is expected
    assert sensitive_write_target(path.replace("/", "\\").upper()) is expected


@pytest.mark.asyncio
async def test_widened_grant_still_blocks_sensitive_writes(tmp_path, fixture_document):
    workspace = tmp_path / "workspace"
    (workspace / "case-001").mkdir(parents=True)
    contract, grant = make_contracts(fixture_document)
    c, g = contract.to_dict(), grant.to_dict()
    c["allowed_effects"] = [
        {"kind": "file.read", "resource": "/workspace/case-001/**"},
        {"kind": "file.write", "resource": "/workspace/case-001/**"},
    ]
    g["effects"] = ["file.read", "file.write"]
    with Receiver() as receiver:
        params = {
            "operations": StdioServerParameters(
                command=sys.executable,
                args=[str(OPERATIONS_SERVER)],
                env={"SUJIE_WORKSPACE_ROOT": str(workspace), "SUJIE_RECEIVER_URL": receiver.url},
            )
        }
        async with StdioMCPProxy(params) as proxy:
            gateway = M1Gateway(proxy, TaskContract(c), TaskGrant(g))
            for path in SENSITIVE:
                result = await gateway.call(
                    "operations.write_file", {"resource": path, "content": "OWNED-SYNTHETIC"}
                )
                assert result["decision"] == "BLOCK", (path, result)
                assert result["code"] == "SENSITIVE_TARGET_FORBIDDEN"
                assert not (workspace / path).exists()
            for path in ORDINARY:
                result = await gateway.call(
                    "operations.write_file", {"resource": path, "content": "ok"}
                )
                assert result["ok"] and result["decision"] == "ALLOW", (path, result)
                assert (workspace / path).read_text("utf-8") == "ok"
