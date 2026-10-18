"""Copy an explicit M24 Linux allowlist only after application/deployment freezes."""

import argparse
import hashlib
import json
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PREFIXES = (
    "gateway-python/src/sujie_gateway",
    "demo-agent/sujie_demo_agent",
    "control-plane-python/sujie_control",
    "sandbox",
)
EXACT_FILES = (
    "requirements.lock",
    "contracts/enums.json",
    "contracts/manifest.json",
    "gateway-python/policies/m1.yaml",
    "assets/tokenizer/qwen3-local-manifest.json",
    "model-cache/qwen3-local/tokenizer.json",
    "mcp-servers/evidence-server/server.py",
    "mcp-servers/operations-server/server.py",
    "mcp-servers/git-delivery-server/server.py",
    "mcp-servers/versioned-memory-server/server.py",
    "deploy/m24/smoke.py",
)
FORBIDDEN_PARTS = {
    ".venv",
    ".control-runtime",
    "node_modules",
    "reports",
    ".git",
    "__pycache__",
    ".aws",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def entry_hash(archive, relative):
    record = archive["files"].get("sujie/" + relative, archive["files"].get(relative))
    return record["sha256"] if isinstance(record, dict) else record


def read_checked(source):
    relative = source.relative_to(ROOT)
    if (
        any(part in FORBIDDEN_PARTS or part.startswith(".env") for part in relative.parts)
        or source.suffix.lower() in {".csv", ".env", ".pem", ".key"}
        or any(path.is_symlink() for path in (source, *source.parents))
        or not stat.S_ISREG(source.lstat().st_mode)
    ):
        raise ValueError("M24_CONTEXT_FORBIDDEN_OR_NONREGULAR_PATH")
    return source.read_bytes()


def prepare(out, freeze_archive, deployment_archive):
    out = Path(out)
    if out.exists():
        raise ValueError("M24_CONTEXT_ALREADY_EXISTS")
    application = json.loads(freeze_archive.read_bytes())
    deployment = json.loads(deployment_archive.read_bytes())
    selected = {ROOT / name for name in EXACT_FILES}
    selected.update(path for prefix in SOURCE_PREFIXES for path in (ROOT / prefix).rglob("*.py"))
    selected.update((ROOT / "eval").glob("*.py"))
    selected.update((ROOT / "contracts/schemas").glob("*.json"))
    files, contents = {}, {}
    for source in sorted(selected):
        relative, raw = source.relative_to(ROOT).as_posix(), read_checked(source)
        expected = entry_hash(
            deployment if relative.startswith("deploy/m24/") else application, relative
        )
        if relative == "model-cache/qwen3-local/tokenizer.json":
            manifest = json.loads(
                (ROOT / "assets/tokenizer/qwen3-local-manifest.json").read_bytes()
            )
            expected = manifest["sha256"]
            if len(raw) != manifest["bytes"]:
                raise ValueError("M24_TOKENIZER_SIZE_MISMATCH")
        if expected is None or digest(raw) != expected:
            raise ValueError("M24_SOURCE_NOT_FROZEN_OR_CHANGED")
        files[relative] = {"sha256": digest(raw), "bytes": len(raw)}
        contents[relative] = raw
    dockerfile = ROOT / "deploy/m24/Dockerfile.smoke"
    docker_raw = read_checked(dockerfile)
    if digest(docker_raw) != entry_hash(deployment, "deploy/m24/Dockerfile.smoke"):
        raise ValueError("M24_DOCKERFILE_CHANGED_AFTER_FREEZE")
    out.mkdir(parents=True)
    for relative, raw in contents.items():
        target = out / "sujie" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (out / "Dockerfile").write_bytes(docker_raw)
    record = {
        "kind": "m24-linux-allowlist-context-v1",
        "application_freeze_sha256": digest(freeze_archive.read_bytes()),
        "deployment_freeze_sha256": digest(deployment_archive.read_bytes()),
        "scope": "allowlisted Python source, contracts, policy, locked dependencies and one pinned public tokenizer; no environment, private CSV, reports, venv, node_modules or user directory mounts",
        "files": files,
        "dockerfile_sha256": digest(docker_raw),
    }
    raw = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    (out / "context-manifest.json").write_bytes(raw)
    print(json.dumps({"files": len(files), "context_manifest_sha256": digest(raw)}))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--freeze-archive", type=Path, required=True)
    parser.add_argument("--deployment-archive", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.out, args.freeze_archive, args.deployment_archive)
