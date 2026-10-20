#!/usr/bin/env python3
"""Generate the report source-binding record for one code baseline.

The record pins an immutable snapshot: a rule-based manifest of runtime sources
plus the regression and evaluation evidence observed for that snapshot. The
report's ``latex/runtime-version.json`` then points at this file and its
SHA-256, so a reviewer can re-derive both the file list and the digests with
``git`` alone — no hand-maintained hash table.

Usage:
  python3 build_report_binding.py --code-baseline <40-hex-sha> \
      --metrics metrics.json --out ../../../docs/validation/<name>.json

``--metrics`` supplies everything that is not derivable from git (test counts,
CI run ids, offline evaluation results). Writing to an existing file is refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

# One reviewable rule, applied to every tracked file under sujie/.
EXCLUDE_PREFIXES = ("sujie/docs/", "sujie/eval/reports/")
EXCLUDE_SUFFIXES = (".sh", ".css", ".html", ".svg", ".mmd", ".dot", ".png")
EXCLUDE_BASENAMES = {"README.md"}


def is_manifest_member(path: str) -> bool:
    if not path.startswith("sujie/"):
        return False
    if path.startswith(EXCLUDE_PREFIXES):
        return False
    basename = os.path.basename(path)
    if basename.startswith(".") or basename in EXCLUDE_BASENAMES:
        return False
    if basename.startswith("Dockerfile"):
        return True
    return not path.endswith(EXCLUDE_SUFFIXES)


def tracked_paths(repo: Path, commit: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", commit, "sujie"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.split()
    return sorted(p for p in out if p and is_manifest_member(p))


def blob_digests(repo: Path, commit: str, paths: list[str]) -> dict[str, str]:
    """SHA-256 of the exact committed bytes (no checkout newline conversion)."""
    result = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo,
        input="".join(f"{commit}:{name}\n" for name in paths).encode("utf-8"),
        capture_output=True, check=True,
    )
    output, offset, digests = result.stdout, 0, {}
    for name in paths:
        end = output.find(b"\n", offset)
        header = output[offset:end].split()
        if end < 0 or len(header) != 3 or not header[2].isdigit():
            raise SystemExit(f"cited blob unavailable: {name}")
        start, size = end + 1, int(header[2])
        digests[name] = hashlib.sha256(output[start : start + size]).hexdigest()
        offset = start + size + 1
    return digests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-baseline", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[3]
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing record: {out}")

    paths = tracked_paths(repo, args.code_baseline)
    digests = blob_digests(repo, args.code_baseline, paths)

    missing = [
        name for name in paths
        if not (repo / name).is_file()
        or hashlib.sha256((repo / name).read_bytes()).hexdigest() != digests[name]
    ]

    record = {
        "schema": "sujie-merged-main-validation-v1",
        "code_baseline": args.code_baseline,
        **json.loads(Path(args.metrics).read_text("utf-8")),
        "manifest_rule": {
            "include": "all tracked files under sujie/",
            "exclude_prefixes": list(EXCLUDE_PREFIXES),
            "exclude_suffixes": list(EXCLUDE_SUFFIXES),
            "exclude_basenames": sorted(EXCLUDE_BASENAMES),
            "note": "dotfiles and README.md excluded; Dockerfile* included; "
                    "digests are SHA-256 of the committed git blobs",
        },
        "manifest_files": len(paths),
        "candidate_source_hashes": digests,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"OK -> {out} ({len(paths)} files)")
    print(f"record_sha256 = {digest}")
    if missing:
        print(f"WARNING: working tree differs from the cited baseline for {len(missing)} file(s):")
        for name in missing[:10]:
            print("  " + name)
        return 1
    print("working tree matches the cited baseline for every manifest file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
