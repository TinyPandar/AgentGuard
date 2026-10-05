"""Bounded input normalization for rule-based detection."""

from __future__ import annotations

import html
import re
import unicodedata

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)
_HTML_TAG = re.compile(r"<[^>]{0,500}>")
_SPACE = re.compile(r"[ \t\f\v]+")
_NEWLINES = re.compile(r"\r\n?|\n{3,}")


def normalize_text(content: str, *, max_chars: int = 100_000) -> str:
    """Normalize common obfuscation without recursive decoding.

    The function is deliberately bounded. It does not attempt unlimited
    Base64, URL, or archive decoding because normalization itself is an
    attacker-controlled resource-consumption surface.
    """

    bounded = content[:max_chars]
    value = unicodedata.normalize("NFKC", bounded)
    value = value.translate(_ZERO_WIDTH)
    value = html.unescape(value)
    value = _HTML_TAG.sub(" ", value)
    value = _SPACE.sub(" ", value)
    value = _NEWLINES.sub("\n", value)
    return value.strip()
