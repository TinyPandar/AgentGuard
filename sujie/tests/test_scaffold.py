import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_SCAFFOLD_001_required_modules_exist():
    for name in (
        "contracts/schemas",
        "gateway-python/src/sujie_gateway",
        "gateway-python/tests",
        "control-plane-java",
        "console-vue",
        "demo-agent",
        "mcp-servers/evidence-server",
        "mcp-servers/operations-server",
        "mcp-servers/malicious-variants",
        "sandbox",
        "eval/cases",
        "eval/attacks",
        "eval/oracles",
        "eval/reports",
        "deploy",
        "docs",
    ):
        assert (ROOT / name).is_dir(), name


def test_SCAFFOLD_002_placeholder_is_not_an_exposed_service():
    data = yaml.safe_load((ROOT / "deploy/compose.yaml").read_text("utf-8"))
    assert set(data["services"]) == {"gateway-placeholder"}
    service = data["services"]["gateway-placeholder"]
    assert service["network_mode"] == "none"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["profiles"] == ["m0"]
    assert not service.get("ports")
    assert not service.get("volumes")
    assert not service.get("privileged")
    assert "placeholder" in service["command"][-1]


def test_SCAFFOLD_003_domain_guards_have_no_service_dependency():
    forbidden = {
        "requests",
        "httpx",
        "socket",
        "sqlalchemy",
        "pymysql",
        "mysql",
        "redis",
        "subprocess",
        "agentguard",
    }
    for path in (ROOT / "gateway-python/src/sujie_gateway").glob("*.py"):
        tree = ast.parse(path.read_text("utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                modules.add((node.module or "").split(".")[0])
        assert not modules & forbidden


def test_SCAFFOLD_004_env_contains_only_fake_values():
    for line in (ROOT / ".env.example").read_text("utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        if any(part in key for part in ("KEY", "PASSWORD", "TOKEN")):
            assert value.startswith("FAKE_")


def test_SCAFFOLD_005_ci_runs_checks():
    workflow = (ROOT.parent / ".github/workflows/sujie-ci.yml").read_text("utf-8")
    data = yaml.safe_load(workflow)
    assert data["permissions"] == {"contents": "read"}
    steps = data["jobs"]["python-check"]["steps"]
    assert any(s.get("run") == "python dev.py check" for s in steps)
    assert any("requirements.lock" in s.get("run", "") for s in steps)
    compose_steps = data["jobs"]["compose-config"]["steps"]
    assert any("deploy/m1.compose.yaml" in s.get("run", "") for s in compose_steps)
