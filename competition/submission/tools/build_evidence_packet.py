#!/usr/bin/env python3
"""Build a desensitized, self-verifying evidence packet for submission.

The packet contains a reproducibility record plus the hash manifest for one or
more evaluation run directories. It never contains credentials, budget ledgers
or personal paths, and it does not claim signature authenticity or ASR.

Usage:
  python3 build_evidence_packet.py --out dist/证据包.zip \
      --run eval/reports/runs/<dir1> [--run eval/reports/runs/<dir2> ...] \
      [--log <path>=<archive-name> ...] \
      [--note "说明文本"]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EXCLUDE_NAMES = {"model-budget.sqlite3", "model-budget.sqlite3-journal"}
EXCLUDE_SUFFIXES = (".sqlite3", ".sqlite3-journal", ".key", ".pem", ".env")
EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "node_modules", "model-cache"}
PATH_RE = re.compile(r"(/Users/[^\"\\s]+|/home/[^\"\\s]+|/private/var/[^\"\\s]+|[A-Za-z]:\\\\[^\"\\s]+)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def included(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    if path.name in EXCLUDE_NAMES or path.name.endswith(EXCLUDE_SUFFIXES):
        return False
    return path.is_file()


def scan_leaks(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not included(path, root) or path.stat().st_size > 8 << 20:
            continue
        try:
            text = path.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        for m in PATH_RE.finditer(text):
            hits.append(f"{path.relative_to(root)}: {m.group(1)[:80]}")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--run", action="append", default=[])
    ap.add_argument("--log", action="append", default=[], help="<path>=<archive-name>")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    leaks: list[str] = []
    members: list[tuple[Path, str]] = []

    for run_arg in args.run:
        run = Path(run_arg)
        if not run.is_dir():
            raise SystemExit(f"run dir not found: {run}")
        leaks += [f"{run.name}/{h}" for h in scan_leaks(run)]
        for path in sorted(run.rglob("*")):
            if included(path, run):
                members.append((path, f"runs/{run.name}/{path.relative_to(run)}"))

    for spec in args.log:
        src, _, name = spec.partition("=")
        name = name or Path(src).name
        path = Path(src)
        if not path.is_file():
            raise SystemExit(f"log not found: {path}")
        name = name.lstrip("/")  # zipfile must not store absolute paths
        members.append((path, f"logs/{name}"))

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, arc in members:
            zf.write(src, arc)
            manifest.append({"path": arc, "bytes": src.stat().st_size, "sha256": sha256(src)})

        reproduce = [
            "# 证据包说明（脱敏）",
            "",
            f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            "- 生成方式：`competition/submission/tools/build_evidence_packet.py`",
            "- 口径限定：**离线档案一致性核验**，不代表签名真实性、实验全成功或攻击成功率（ASR）。",
            "- 排除内容：云凭据、本地预算账本（`*.sqlite3`）、个人环境与缓存。",
            "",
            "## 复现命令",
            "",
            "```sh",
            "cd sujie",
            ".venv/bin/python eval/run_business_validation.py \\",
            "  --protocol-file eval/protocols/four_business_workflows_v2.json \\",
            "  --out-dir eval/reports/runs/<新目录>",
            ".venv/bin/python eval/verify_runtime_validation.py eval/reports/runs/<新目录>",
            ".venv/bin/python dev.py eval-detection",
            "```",
            "",
            "## 目录",
            "",
            "- `runs/<dir>/summary.json`：总体结果与源码归档 SHA-256。",
            "- `runs/<dir>/*-report.txt`：各用例业务报告。",
            "- `runs/<dir>/*-export.json`：各用例运行导出（来源与工具轨迹）。",
            "- `runs/<dir>/runtime-sources.json`：运行时源码快照索引。",
            "- `logs/`：控制台复现日志。",
            "",
        ]
        if args.note:
            reproduce += ["## 备注", "", args.note, ""]
        zf.writestr("README.md", "\n".join(reproduce))
        zf.writestr("manifest.json", json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "scope": "LOCAL_ARCHIVE_EXPORT_CONSISTENCY_NOT_SIGNED_AUTHENTICITY_OR_ASR",
                "files": manifest,
                "leak_scan": {"paths_checked": True, "hits": leaks},
            },
            ensure_ascii=False, indent=2,
        ))
        zf.writestr("MANIFEST.sha256", "\n".join(f"{m['sha256']}  {m['path']}" for m in manifest) + "\n")

    print(f"OK -> {out} ({out.stat().st_size} bytes, {len(manifest)} files)")
    if leaks:
        print(f"WARNING: {len(leaks)} potential path leaks:")
        for hit in leaks[:10]:
            print("  " + hit)
    else:
        print("leak scan: no personal absolute paths found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
