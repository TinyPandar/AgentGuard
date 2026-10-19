import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sujie_gateway import detection, detection_v2
from sujie_gateway.detector import DEFAULT_DETECTOR, get_detector

ROOT = Path(__file__).resolve().parents[1]


def test_default_is_extended_and_frozen_is_selectable(monkeypatch):
    monkeypatch.delenv("SUJIE_DETECTOR", raising=False)
    assert DEFAULT_DETECTOR == "extended" and get_detector() is detection_v2
    monkeypatch.setenv("SUJIE_DETECTOR", "frozen")
    assert get_detector() is detection
    assert get_detector("extended") is detection_v2
    with pytest.raises(ValueError, match="UNKNOWN_DETECTOR"):
        get_detector("nope")
    assert detection.DETECTOR_VERSION != detection_v2.DETECTOR_VERSION


@pytest.mark.parametrize("name", ["frozen", "extended"])
def test_gateway_binds_selected_detector(name):
    code = "import sujie_gateway.m1_runtime as m; print(m.DETECTOR_VERSION)"
    env = dict(os.environ)
    env["SUJIE_DETECTOR"] = name
    env["PYTHONPATH"] = str(ROOT / "gateway-python/src") + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == get_detector(name).DETECTOR_VERSION


def test_frozen_detector_matches_task_aware_protocol_hash():
    import hashlib

    protocol = json.loads((ROOT / "eval/protocols/task_aware_holdout_v1.json").read_text("utf-8"))
    pinned = protocol["implementation_sha256"]["gateway-python/src/sujie_gateway/detection.py"]
    raw = (ROOT / "gateway-python/src/sujie_gateway/detection.py").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pinned
