"""Detector selection.

``detection`` is the frozen rules-v0.3 module pinned byte-for-byte by
``eval/task_aware_protocol.py`` (task-aware held-out protocol); never edit it.
``detection_v2`` is the separately versioned extended detector (seven bypass
families, public-dataset rules, structural Chinese rules).

The gateway runtime defaults to the extended detector. Set
``SUJIE_DETECTOR=frozen`` (or pass ``detector="frozen"`` to ``M1Gateway``) to
reproduce the frozen-detector behaviour.
"""

from __future__ import annotations

import os
from types import ModuleType

from . import detection, detection_v2

DETECTORS: dict[str, ModuleType] = {"frozen": detection, "extended": detection_v2}
DEFAULT_DETECTOR = "extended"
ENV_VAR = "SUJIE_DETECTOR"

# Raised only by the extended detector; the frozen one truncates instead.
ScanLimitExceeded = detection_v2.ScanLimitExceeded


def get_detector(name: str | None = None) -> ModuleType:
    key = name or os.environ.get(ENV_VAR) or DEFAULT_DETECTOR
    try:
        return DETECTORS[key]
    except KeyError:
        raise ValueError("UNKNOWN_DETECTOR") from None
