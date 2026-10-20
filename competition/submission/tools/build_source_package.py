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
TOKEN_RE = re.compile(r"(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{12,})")
PEM_RE = re.compile(r"-----BEGIN ([A-Z ]*PRIVATE KEY)-----\s*(.*?)\s*-----END \1-----", re.S)
# Fixtures that announce themselves as non-functional key material (e.g. tests proving
# masking) are reported separately so real credentials are not buried in noise.
SYNTHETIC_MARKER_RE = re.compile(
    r"(synthetic|non-?functional|do-?not-?use|demo[- _]?key|fixture|placeholder|假密钥|测试用)",
    re.I,
)


def scan_text(text: str) -> str:
    """Classify one file body: 'real' credential, 'synthetic' fixture, or 'clean'."""
    if TOKEN_RE.search(text):
        return "real"
    verdicts: list[str] = []
    for match in PEM_RE.finditer(text):
        body = re.sub(r"[^A-Za-z0-9+/=]", "", match.group(2))
        window = text[max(0, match.start() - 800) : match.end() + 800]
        # Real private keys carry far more than 64 base64 chars; short bodies are placeholders.
        if len(body) < 64 or SYNTHETIC_MARKER_RE.search(window):
            verdicts.append("synthetic")
        else:
            verdicts.append("real")
    if "real" in verdicts:
        return "real"
    return "synthetic" if verdicts else "clean"

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
    synthetic: list[str] = []
    for path, arc in files:
        if path.stat().st_size > 4 << 20:
            continue
        text = path.read_text("utf-8", errors="ignore")
        verdict = scan_text(text)
        if verdict == "real":
            suspects.append(arc)
        elif verdict == "synthetic":
            synthetic.append(arc)

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
    if synthetic:
        print(f"note: {len(synthetic)} file(s) carry self-labelled synthetic key fixtures:")
        for s in synthetic:
            print("  " + s)
    if suspects:
        print("WARNING: credential-like strings found (no synthetic marker):")
        for s in suspects:
            print("  " + s)
        return 1
    print("credential scan: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
