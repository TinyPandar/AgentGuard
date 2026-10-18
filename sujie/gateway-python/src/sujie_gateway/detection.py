"""Bounded, explainable first-pass scan of untrusted tool output."""

from __future__ import annotations

import base64
import binascii
import html
import re
import unicodedata
from urllib.parse import unquote

from .contracts import DetectionFinding

DETECTOR_VERSION = "rules-v0.4"
MAX_SCAN_CHARS = 1_000_000
OVERRIDE_PATTERNS = (
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.I),
    re.compile(r"(?:忽略|无视)(?:原|之前|先前|以上|所有|当前)?(?:任务|指令|规则)"),
)
AGENT_DIRECTIVE = re.compile(
    r"\b(?:you\s+)?(?:must|should|always|please)\s+"
    r"(?:(?:first|also|now|then|automatically|immediately)\s+){0,3}"
    r"(?:call|execute|run|send|access|update|modify|change|redirect|fetch|delete|upload|display|state|use|ignore|set|perform|make|clean|read|remove)\b",
    re.I,
)
PARAMETER_REWRITE = re.compile(
    r"\b(?:query|parameter|argument|input)\s+is\s+(?:automatically\s+)?"
    r"(?:modified|changed|rewritten|enhanced)\s+to\s+(?:include|add|replace|use)\b",
    re.I,
)
SELF_TOOL_GUIDANCE = re.compile(
    r"\s+this\s+tool\s+when(?:ever)?\s+(?:(?:the\s+)?user\b|asked\b)", re.I
)
CONCEALMENT_DIRECTIVE = re.compile(
    r"\b(?:must|should|do)\s+not\s+(?:inform|tell|notify|mention)\s+(?:the\s+)?user\b",
    re.I,
)


def normalized_view(content: str) -> str:
    """Make an inspection view while leaving the stored source untouched."""
    view = unicodedata.normalize("NFKC", content[:MAX_SCAN_CHARS])[:MAX_SCAN_CHARS]
    view = "".join(char for char in view if unicodedata.category(char) != "Cf")
    for _ in range(2):
        decoded = unicodedata.normalize("NFKC", html.unescape(unquote(view)))[:MAX_SCAN_CHARS]
        if decoded == view:
            break
        view = decoded
    return view


# The seven bypass families are evaluation labels, not claims of attack intent.
# Keep raw evidence separate from normalized/decoded scanning views.
EXTRA_OVERRIDE_PATTERNS = (
    re.compile(r"(?:以前の指示を無視|前の指示を無視|これまでの指示を無視)"),
    re.compile(r"игнорируй\s+(?:предыдущие|прошлые)\s+инструкции", re.I),
    re.compile(
        r"i[^\w]{0,3}g[^\w]{0,3}n[^\w]{0,3}o[^\w]{0,3}r[^\w]{0,3}e\s+"
        r"(?:previous|prior)\s+instructions", re.I
    ),
)
FORGED_AUTHORITY = re.compile(
    r"(?:审批|授权|批准).{0,25}(?:已|管理员|主管|完成|通过)"
    r"|(?:管理员|主管).{0,25}(?:批准|授权|审批)"
    r"|\b(?:approval\s+(?:has\s+been\s+)?granted"
    r"|admin(?:istrator)?\s+(?:has\s+)?approved|already\s+authorized)\b",
    re.I,
)
SENSITIVE_EFFECT = re.compile(
    r"(?:凭据|密钥|令牌|密码|secret|credential|token|secret\.txt)"
    r".{0,90}(?:发送|上传|外发|交给|传输|send|upload|transfer)"
    r"|(?:发送|上传|外发|交给|传输|send|upload|transfer)"
    r".{0,90}(?:凭据|密钥|令牌|密码|secret|credential|token|secret\.txt)",
    re.I,
)
FRAGMENT_MARKER = re.compile(r"(?:片段[一二三四五六七八九十\d]+|fragment\s*\d+)\s*[:：]\s*", re.I)
BASE64_FIELD = re.compile(
    r"\b(?:payload_b64|instruction_b64|base64)\s*[:=]\s*([A-Za-z0-9_+/=-]{12,8192})",
    re.I,
)
ESCAPED_UNICODE = re.compile(r"\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})")
QUOTED_TRAINING = re.compile(
    r"(?:培训资料引用|(?:training|example)\s+(?:material\s+)?(?:quotes?|cites?))"
    r".{0,200}(?:供分析|不要求执行|do\s+not\s+execute|for\s+analysis)",
    re.I | re.S,
)
LOOKALIKES = str.maketrans(
    {"і": "i", "ӏ": "l", "о": "o", "а": "a", "е": "e", "р": "p", "с": "c", "ԁ": "d"}
)
MAX_SEGMENTS = 32


class ScanLimitExceeded(ValueError):
    """An incomplete scan cannot be interpreted as a clean result."""


def _strict_view(content: str) -> str:
    """Scan every code point or reject; normalization expansion cannot hide the tail."""
    view = unicodedata.normalize("NFKC", content)
    if len(view) > MAX_SCAN_CHARS:
        raise ScanLimitExceeded("CONTENT_SCAN_LIMIT_EXCEEDED")
    view = "".join(char for char in view if unicodedata.category(char) != "Cf")
    for _ in range(2):
        decoded = unicodedata.normalize("NFKC", html.unescape(unquote(view)))
        if len(decoded) > MAX_SCAN_CHARS:
            raise ScanLimitExceeded("CONTENT_SCAN_LIMIT_EXCEEDED")
        if decoded == view:
            break
        view = decoded
    return view


def _candidates(view: str) -> tuple[str, ...]:
    candidates = [view, view.translate(LOOKALIKES)]
    unescaped = ESCAPED_UNICODE.sub(lambda m: chr(int(m.group(1) or m.group(2), 16)), view)
    if unescaped != view:
        candidates.append(_strict_view(unescaped))
    for match in BASE64_FIELD.finditer(view):
        try:
            data = base64.b64decode(
                match.group(1).replace("-", "+").replace("_", "/"), validate=True
            )
            decoded = data.decode("utf-8")
        except (ValueError, UnicodeError, binascii.Error):
            continue
        if len(decoded) <= 8192:
            candidates.append(_strict_view(decoded))
    return tuple(dict.fromkeys(candidates))


def _fragments(view: str) -> str:
    matches = list(FRAGMENT_MARKER.finditer(view))
    if not 2 <= len(matches) <= 16:
        return ""
    pieces = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(view)
        piece = view[match.end():end].strip(" \t\r\n；;，,。.")
        if len(piece) > 512:
            return ""
        pieces.append(piece)
    return "".join(pieces)


def _scan(view: str) -> tuple[str, str] | None:
    for candidate in _candidates(view):
        # Narrow evidence-only exemption; an extra executable clause is still scanned.
        if QUOTED_TRAINING.fullmatch(candidate.strip().rstrip("。.!！")):
            continue
        override = any(
            pattern.search(candidate) for pattern in (*OVERRIDE_PATTERNS, *EXTRA_OVERRIDE_PATTERNS)
        )
        if override:
            return "CONTEXT_HIJACK", "untrusted_text_requests_instruction_override"
        if FORGED_AUTHORITY.search(candidate) and SENSITIVE_EFFECT.search(candidate):
            return "AUTHORIZATION_FORGERY", "untrusted_text_claims_authority_for_sensitive_effect"
        directive = bool(
            CONCEALMENT_DIRECTIVE.search(candidate) or PARAMETER_REWRITE.search(candidate)
        )
        for match in AGENT_DIRECTIVE.finditer(candidate):
            if (
                match.group().lower().rstrip().endswith(("call", "use"))
                and SELF_TOOL_GUIDANCE.match(candidate, match.end())
            ):
                continue
            directive = True
            break
        if directive:
            return "TOOL_POISONING", "untrusted_text_directs_agent_action"
        fragment = _fragments(candidate)
        if fragment and any(
            pattern.search(fragment) for pattern in (*OVERRIDE_PATTERNS, *EXTRA_OVERRIDE_PATTERNS)
        ):
            return "CONTEXT_HIJACK", "untrusted_fragments_reconstruct_override"
        if (
            fragment
            and re.search(r"(?:拼接.{0,15}执行|解码后执行)", candidate)
            and SENSITIVE_EFFECT.search(fragment)
        ):
            return "TOOL_POISONING", "untrusted_fragments_direct_sensitive_effect"
    return None


def _finding(
    spans: list[dict],
    finding_id: str,
    artifact_id: str,
    attack_source: str,
    result: tuple[str, str],
) -> DetectionFinding:
    family, reason = result
    return DetectionFinding(
        {
            "schema_version": "1.0",
            "finding_id": finding_id,
            "attack_source": attack_source,
            "attack_family": family,
            "spans": spans,
            "normalized_view": f"evidence://view/{artifact_id}/nfkc-v1",
            "confidence": 0.8,
            "reasons": [reason],
            "detector_version": DETECTOR_VERSION,
        }
    )


def detect_indirect(
    content: str, artifact_id: str, finding_id: str, *, attack_source: str = "INDIRECT"
) -> tuple[str, DetectionFinding | None]:
    """Advisory finding over complete bounded source; never silently drop the tail."""
    if not isinstance(content, str):
        raise TypeError("CONTENT_NOT_TEXT")
    if len(content) > MAX_SCAN_CHARS:
        raise ScanLimitExceeded("CONTENT_SCAN_LIMIT_EXCEEDED")
    view = _strict_view(content)
    result = _scan(view)
    if result is None:
        return view, None
    return view, _finding(
        [{"artifact_id": artifact_id, "start": 0, "end": len(content)}],
        finding_id,
        artifact_id,
        attack_source,
        result,
    )


def detect_indirect_segments(
    segments: list[tuple[str, str]], finding_id: str, *, attack_source: str = "INDIRECT"
) -> tuple[str, DetectionFinding | None]:
    """Scan Host-verified ordered segments sharing a trust context.

    This API does not auto-combine unrelated turns. All conservative source
    spans are reported; normalized positions are not raw-source offsets.
    """
    if not 1 <= len(segments) <= MAX_SEGMENTS or any(
        not isinstance(sid, str) or not isinstance(content, str)
        for sid, content in segments
    ):
        raise ValueError("INVALID_SCAN_SEGMENTS")
    if len({sid for sid, _ in segments}) != len(segments):
        raise ValueError("DUPLICATE_SCAN_SOURCE")
    if sum(len(value) for _, value in segments) > MAX_SCAN_CHARS:
        raise ScanLimitExceeded("CONTENT_SCAN_LIMIT_EXCEEDED")
    views = [_strict_view(value) for _, value in segments]
    if sum(map(len, views)) > MAX_SCAN_CHARS:
        raise ScanLimitExceeded("CONTENT_SCAN_LIMIT_EXCEEDED")
    view = "\n".join(views)
    result = next((hit for part in views if (hit := _scan(part)) is not None), None)
    if result is None:
        result = _scan("".join(views)) or _scan(view)
    if result is None:
        return view, None
    spans = [{"artifact_id": sid, "start": 0, "end": len(value)} for sid, value in segments]
    return view, _finding(spans, finding_id, segments[0][0], attack_source, result)
