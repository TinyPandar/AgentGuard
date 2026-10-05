"""Explainable baseline detector.

This detector supplies risk signals only. It never grants permissions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agentguard.models import Delivery, RiskLevel, ScanResult

from .normalizer import normalize_text


@dataclass(frozen=True)
class _Rule:
    attack_type: str
    pattern: re.Pattern[str]
    score: float


class RuleDetector:
    def __init__(self) -> None:
        flags = re.IGNORECASE | re.DOTALL
        self._rules = (
            _Rule(
                "INSTRUCTION_OVERRIDE",
                re.compile(
                    r"(?:ignore|disregard|forget|忽略|无视).{0,50}"
                    r"(?:previous|prior|above|system|此前|之前|以上|系统).{0,20}"
                    r"(?:instruction|prompt|指令|提示)",
                    flags,
                ),
                0.90,
            ),
            _Rule(
                "PROMPT_LEAKAGE",
                re.compile(
                    r"(?:reveal|show|print|输出|显示|泄露).{0,40}"
                    r"(?:system prompt|developer message|系统提示词|开发者指令)",
                    flags,
                ),
                0.88,
            ),
            _Rule(
                "ROLE_MANIPULATION",
                re.compile(
                    r"(?:you are now|act as|switch role|现在你是|扮演|切换角色)", flags
                ),
                0.72,
            ),
            _Rule(
                "TOOL_MANIPULATION",
                re.compile(
                    r"(?:call|invoke|execute|调用|执行).{0,40}"
                    r"(?:tool|function|command|工具|函数|命令|send_external|export_sensitive)",
                    flags,
                ),
                0.86,
            ),
            _Rule(
                "CONFIRMATION_FORGERY",
                re.compile(
                    r"(?:user|用户).{0,30}(?:already approved|has approved|已经批准|已确认)",
                    flags,
                ),
                0.82,
            ),
            _Rule(
                "DATA_EXFILTRATION",
                re.compile(
                    r"(?:send|upload|post|发送|上传|外传).{0,80}"
                    r"(?:secret|token|report|contact|internal|敏感|密钥|报告|联系人|内部)",
                    flags,
                ),
                0.92,
            ),
        )

    def scan(
        self,
        content: str,
        *,
        source_type: str = "USER_INPUT",
        delivery: Delivery = Delivery.DIRECT,
    ) -> ScanResult:
        normalized = normalize_text(content)
        matches: list[tuple[_Rule, str]] = []
        for rule in self._rules:
            match = rule.pattern.search(normalized)
            if match:
                matches.append((rule, match.group(0)[:160]))

        if not matches:
            return ScanResult(
                risk_score=0.05,
                risk_level=RiskLevel.LOW,
                delivery=delivery,
                source_type=source_type,
            )

        score = max(rule.score for rule, _ in matches)
        if len(matches) >= 2:
            score = min(1.0, score + 0.05)
        if score >= 0.9:
            level = RiskLevel.CRITICAL
        elif score >= 0.7:
            level = RiskLevel.HIGH
        elif score >= 0.4:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        return ScanResult(
            risk_score=score,
            risk_level=level,
            attack_types=tuple(sorted({rule.attack_type for rule, _ in matches})),
            evidence=tuple(evidence for _, evidence in matches),
            delivery=delivery,
            source_type=source_type,
        )
