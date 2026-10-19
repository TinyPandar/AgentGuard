"""Download pinned public injection datasets and (re)build the committed sample.

    python eval/fetch_public_injection.py                 # full sets into eval/.cache
    python eval/fetch_public_injection.py --write-sample  # also rebuild fixture

Full data needs network and ``pyarrow``; tests only use the committed sample.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from public_injection_sources import SOURCES  # noqa: E402

CACHE = ROOT / "eval/.cache/public_injection"
SAMPLE = ROOT / "eval/cases/public_injection_sample_v1.json"
PER_CLASS = 20
MAX_TEXT = 4000


def fetch(source) -> list[dict]:
    rows = []
    for path in source.files:
        target = CACHE / source.source_id / Path(path).name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(source.url(path), timeout=60) as resp:
                target.write_bytes(resp.read())
        raw = target.read_bytes()
        for i, row in enumerate(source.rows(path, raw)):
            row.setdefault("upstream_id", f"{Path(path).stem}:{i}")
            rows.append(row)
    out = CACHE / f"{source.source_id}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    return rows


def sample(source, rows: list[dict]) -> list[dict]:
    rng = random.Random(f"public-injection-v1:{source.source_id}")
    picked = []
    for label in (True, False):
        pool = [r for r in rows if r["attack"] is label and len(r["text"]) <= MAX_TEXT]
        picked += rng.sample(pool, min(PER_CLASS, len(pool)))
    return [
        {
            "id": f"{source.source_id}:{r['upstream_id']}",
            "source": source.source_id,
            "attack_source": source.attack_source,
            **r,
        }
        for r in picked
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-sample", action="store_true")
    args = parser.parse_args()
    cases, meta = [], []
    for source in SOURCES:
        rows = fetch(source)
        print(f"{source.source_id}: {len(rows)} rows ({source.licence})")
        meta.append(
            {
                "source_id": source.source_id,
                "repo": source.repo,
                "revision": source.revision,
                "licence": source.licence,
                "capability": source.capability,
                "full_rows": len(rows),
                "sampled": source.commit_sample,
            }
        )
        if source.commit_sample:
            cases += sample(source, rows)
    if args.write_sample:
        body = {
            "dataset_id": "public-injection-sample-v1",
            "scope": "rule-detector-only-not-agent-asr",
            "note": "Stratified sample (<=20 attack + <=20 benign per source, seed fixed) "
            "from redistributable sources only; attribution per licence.",
            "sources": meta,
            "cases": cases,
        }
        SAMPLE.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", "utf-8")
        print("sample", len(cases), hashlib.sha256(SAMPLE.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
