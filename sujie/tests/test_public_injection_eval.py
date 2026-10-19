import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REDISTRIBUTABLE = {"Apache-2.0", "MIT", "CC-BY-4.0"}


def test_sample_only_contains_redistributable_pinned_sources():
    data = json.loads((ROOT / "eval/cases/public_injection_sample_v1.json").read_text("utf-8"))
    meta = {m["source_id"]: m for m in data["sources"]}
    used = {case["source"] for case in data["cases"]}
    assert used == {"deepset", "gandalf", "mcp_tool_poisoning", "agent_safety_bench_zh"}
    for sid in used:
        assert meta[sid]["licence"] in REDISTRIBUTABLE and len(meta[sid]["revision"]) == 40
    assert len({case["id"] for case in data["cases"]}) == len(data["cases"]) == 140


def test_public_sample_metrics_are_reported_per_source():
    report = runpy.run_path(str(ROOT / "eval/run_public_injection.py"))["evaluate_sample"]()
    assert report["evaluation_scope"] == "rule_detector_only_not_agent_asr"
    assert report["overall"]["n"] == 140
    assert set(report["per_source"]) == {
        "deepset",
        "gandalf",
        "mcp_tool_poisoning",
        "agent_safety_bench_zh",
    }
    # Benign contrasts must stay clean; recall is tracked, not asserted (baseline is low).
    assert report["overall"]["confusion"]["fp"] == 0
