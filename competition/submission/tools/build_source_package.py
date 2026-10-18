#!/usr/bin/env python3
"""Package the submission source tree for the '可执行程序' deliverable.

Contains source, tests, design docs and the one-key dev entry (sujie/dev.py).
Excludes virtual environments, caches, model caches, local runtime state,
budget ledgers, credentials, raw evaluation runs and any git history.

Usage:
  python3 build_source_package.py --out dist/源码包.zip [--root .]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

INCLUDE_TOP = ["sujie", "competition", "docs", "artifacts"]
INCLUDE_FILES = ["README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", ".env.example"]

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    "model-cache", ".control-runtime", "dist", "htmlcov", ".mypy_cache", ".codex-doc-review",
}
EXCLUDE_SUFFIXES = (
    ".sqlite3", ".sqlite3-journal", ".pyc", ".pyo", ".log", ".key", ".pem", ".p12", ".pfx",
    ".DS_Store",
)
EXCLUDE_NAME_RE = re.compile(r"(credential|secret|api[_-]?key|honeytoken)", re.I)
CRED_LINE_RE = re.compile(r"(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")

# Raw evaluation runs are handed over as a separate desensitized packet.
EXCLUDE_PATH_PARTS = {("sujie", "eval", "reports", "runs")}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_excluded(rel: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return True
    if rel.name in ("",) or rel.name.startswith(".") and rel.name not in (".env.example", ".gitignore", ".gitattributes"):
        return True
    if rel.name.endswith(EXCLUDE_SUFFIXES):
        return True
    if EXCLUDE_NAME_RE.search(rel.name):
        return True
    for parts in EXCLUDE_PATH_PARTS:
        if tuple(rel.parts[: len(parts)]) == parts:
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    files: list[tuple[Path, str]] = []
    for top in INCLUDE_TOP:
        base = root / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and not is_excluded(rel):
                files.append((path, rel.as_posix()))
    for name in INCLUDE_FILES:
        path = root / name
        if path.is_file():
            files.append((path, name))

    suspects: list[str] = []
    for path, arc in files:
        if path.stat().st_size > 4 << 20:
            continue
        text = path.read_text("utf-8", errors="ignore")
        if CRED_LINE_RE.search(text):
            suspects.append(arc)

    manifest = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arc in files:
            zf.write(path, arc)
            manifest.append({"path": arc, "bytes": path.stat().st_size, "sha256": sha256(path)})
        zf.writestr("PACKAGE_README.md", "\n".join([
            "# 溯界（Sujie）提交源码包",
            "",
            f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            "- 安装、启动与复现步骤见 `competition/submission/部署说明-溯界.md`。",
            "- 快速入口：`cd sujie && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.lock`，"
            "随后 `.venv/bin/python dev.py demo` / `dev.py console` / `dev.py check`。",
            "- 本包**不含**虚拟环境、依赖缓存、模型缓存、本地运行状态、预算账本、任何凭据与原始评测运行记录。",
            "- 原始评测运行记录另行以脱敏证据包移交。",
            "",
        ]))
        zf.writestr("PACKAGE_MANIFEST.json", json.dumps(
            {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "file_count": len(manifest), "files": manifest},
            ensure_ascii=False, indent=2,
        ))

    print(f"OK -> {out} ({out.stat().st_size} bytes, {len(files)} files)")
    if suspects:
        print("WARNING: credential-like strings found:")
        for s in suspects:
            print("  " + s)
    else:
        print("credential scan: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
