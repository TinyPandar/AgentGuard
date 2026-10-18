"""Create a new Docker context by explicit source/asset allowlists, never a repo tar."""

import argparse
import hashlib
import json
import shutil
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
    "deploy/m23/smoke.py",
)
FORBIDDEN_PARTS = {".venv", ".control-runtime", "node_modules", "reports", ".git", "__pycache__"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def copy_checked(source, target):
    relative = source.relative_to(ROOT)
    if any(part in FORBIDDEN_PARTS for part in relative.parts) or source.suffix == ".csv":
        raise ValueError("CONTEXT_FORBIDDEN_PATH")
    if any(path.is_symlink() for path in (source, *source.parents) if path != ROOT.parent):
        raise ValueError("CONTEXT_SYMLINK_REFUSED")
    raw = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return {"sha256": digest(raw), "bytes": len(raw)}


def prepare(out, *, mode, freeze_archive=None):
    if out.exists():
        raise ValueError("CONTEXT_ALREADY_EXISTS")
    out.mkdir(parents=True)
    files = {}
    if mode == "dependencies":
        selected = [ROOT / "requirements.lock"]
        dockerfile = ROOT / "deploy/m23/Dockerfile.dependencies"
    else:
        if freeze_archive is None:
            raise ValueError("RUNTIME_CONTEXT_REQUIRES_FREEZE_ARCHIVE")
        selected = [ROOT / name for name in EXACT_FILES]
        selected += [path for prefix in SOURCE_PREFIXES for path in (ROOT / prefix).rglob("*.py")]
        selected += sorted((ROOT / "eval").glob("*.py"))
        selected += sorted((ROOT / "contracts/schemas").glob("*.json"))
        dockerfile = ROOT / "deploy/m23/Dockerfile.smoke"
    archive = json.loads(freeze_archive.read_bytes()) if freeze_archive else None
    for source in sorted(set(selected)):
        relative = source.relative_to(ROOT).as_posix()
        target = out / ("sujie/" + relative if mode == "runtime" else relative)
        record = copy_checked(source, target)
        if archive:
            expected = archive["files"].get("sujie/" + relative, archive["files"].get(relative))
            if isinstance(expected, dict):
                expected = expected["sha256"]
            if expected is None and not relative.startswith(("deploy/m23/", "model-cache/")):
                raise ValueError("RUNTIME_SOURCE_NOT_IN_FREEZE_MANIFEST")
            if expected is not None and record["sha256"] != expected:
                raise ValueError("RUNTIME_SOURCE_CHANGED_AFTER_FREEZE")
        files[relative] = record
    if mode == "runtime":
        manifest = json.loads((ROOT / "assets/tokenizer/qwen3-local-manifest.json").read_bytes())
        asset = files["model-cache/qwen3-local/tokenizer.json"]
        if asset != {"sha256": manifest["sha256"], "bytes": manifest["bytes"]}:
            raise ValueError("TOKENIZER_ASSET_MISMATCH")
    shutil.copyfile(dockerfile, out / "Dockerfile")
    record = {
        "kind": "m23-linux-allowlist-context-v1",
        "mode": mode,
        "scope": "explicit Python source, contracts, policy, locked dependencies and one pinned public tokenizer; no environment, credentials, reports, frontend dependencies or user directories",
        "source_archive_sha256": digest(freeze_archive.read_bytes()) if freeze_archive else None,
        "files": files,
        "dockerfile_sha256": digest(dockerfile.read_bytes()),
    }
    data = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    (out / "context-manifest.json").write_bytes(data)
    print(json.dumps({"files": len(files), "context_manifest_sha256": digest(data), "mode": mode}))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("dependencies", "runtime"), required=True)
    parser.add_argument("--freeze-archive", type=Path)
    args = parser.parse_args()
    prepare(args.out, mode=args.mode, freeze_archive=args.freeze_archive)
