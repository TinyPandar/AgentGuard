"""Registry of verified public prompt-injection datasets (pinned revisions).

Only sources whose licence permits redistribution may contribute committed
sample fixtures (``commit_sample=True``). Others are download-only and are
cached under ``eval/.cache/public_injection`` (ignored by git).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Iterable

HF = "https://huggingface.co/datasets/{repo}/resolve/{rev}/{path}"


@dataclass(frozen=True)
class Source:
    source_id: str
    repo: str
    revision: str
    files: tuple[str, ...]
    licence: str
    commit_sample: bool
    capability: str
    attack_source: str
    rows: Callable[[str, bytes], Iterable[dict]]
    train_files: tuple[str, ...] = ()

    def url(self, path: str) -> str:
        return HF.format(repo=self.repo, rev=self.revision, path=path)


def _parquet(raw: bytes) -> list[dict]:
    import io

    import pyarrow.parquet as pq  # optional dependency, only for full download

    return pq.read_table(io.BytesIO(raw)).to_pylist()


def _jsonl(raw: bytes) -> list[dict]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def _deepset(path: str, raw: bytes):
    for row in _parquet(raw):
        yield {"text": row["text"], "attack": bool(row["label"]), "lang": "en/de"}


def _gandalf(path: str, raw: bytes):
    for row in _parquet(raw):  # attack-only set
        yield {"text": row["text"], "attack": True, "lang": "en"}


def _mtp(path: str, raw: bytes):
    for row in _jsonl(raw):
        yield {
            "text": row["benign_description"],
            "attack": False,
            "lang": "en",
            "family": "MCP_TOOL_DESCRIPTION",
            "upstream_id": row["id"] + ":benign",
        }
        yield {
            "text": row["poisoned_description"],
            "attack": True,
            "lang": "en",
            "family": "MCP_TOOL_DESCRIPTION:" + row.get("technique", ""),
            "upstream_id": row["id"] + ":poisoned",
        }


def _asb_zh(path: str, raw: bytes):
    for row in _jsonl(raw):
        if row["category"] not in {"benign", "prompt_injection"}:
            continue  # destructive actions are policy/DSL territory, not text injection
        text = row["context"] + "\n" + json.dumps(row["action"], ensure_ascii=False)
        yield {
            "text": text,
            "attack": row["category"] == "prompt_injection",
            "lang": "zh",
            "upstream_id": row["id"],
            "family": row["difficulty"],
        }


def _eric_zh(path: str, raw: bytes):
    for row in _parquet(raw):
        if row.get("taiwan_translation"):
            yield {
                "text": row["taiwan_translation"],
                "attack": row["completion"] == "Yes",
                "lang": "zh-Hant",
            }


def _xtram(path: str, raw: bytes):
    for row in _parquet(raw):
        yield {"text": row["text"], "attack": bool(row["label"]), "lang": "en"}


SOURCES = (
    Source(
        "deepset",
        "deepset/prompt-injections",
        "4f61ecb038e9c3fb77e21034b22511b523772cdd",
        ("data/test-00000-of-00001-701d16158af87368.parquet",),
        "Apache-2.0",
        True,
        "DIRECT (en/de, mixed-language)",
        "DIRECT",
        _deepset,
        train_files=("data/train-00000-of-00001-9564e8b05b4757ab.parquet",),
    ),
    Source(
        "gandalf",
        "Lakera/gandalf_ignore_instructions",
        "04737b65e90a6794ec227012e4a255a7def6344b",
        ("data/test-00000-of-00001-bc92128b9288a6d1.parquet",),
        "MIT",
        True,
        "DIRECT override (attack-only, recall)",
        "DIRECT",
        _gandalf,
        train_files=("data/train-00000-of-00001-ded53be747ff55cd.parquet",),
    ),
    Source(
        "mcp_tool_poisoning",
        "fevziegeyurtsevenler/mcp-tool-poisoning",
        "9b7a1088526d424c518d856ba5204f935a279727",
        ("mtp.jsonl",),
        "Apache-2.0",
        True,
        "INDIRECT: MCP tool-description poisoning (paired benign/poisoned)",
        "INDIRECT",
        _mtp,
    ),
    Source(
        "agent_safety_bench_zh",
        "uninhibited-scholar/agent-safety-bench-zh",
        "4089ae3e13ce3c23872c3d47d8b199d40e117aa2",
        ("test.jsonl",),
        "CC-BY-4.0",
        True,
        "Chinese agent tool-call injection vs benign",
        "INDIRECT",
        _asb_zh,
    ),
    Source(
        "pi_benchmark_zh",
        "Eric12132/prompt-injections-benchmark-chinese",
        "0fb4ff375fbe0c57073d5185e362ae4cafa54b96",
        ("data/test-00000-of-00001.parquet",),
        "unspecified",
        False,
        "Chinese (Traditional) injection/jailbreak, download-only",
        "DIRECT",
        _eric_zh,
        train_files=("data/train-00000-of-00001.parquet",),
    ),
    Source(
        "safe_guard",
        "xTRam1/safe-guard-prompt-injection",
        "a3a877d608f37b7d20d9945671902df895ecdb46",
        ("data/test-00000-of-00001.parquet",),
        "unspecified",
        False,
        "DIRECT synthetic (en), download-only",
        "DIRECT",
        _xtram,
        train_files=("data/train-00000-of-00001.parquet",),
    ),
)
BY_ID = {s.source_id: s for s in SOURCES}
