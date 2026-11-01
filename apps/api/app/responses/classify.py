"""Deterministic classifier for recruiter reply emails."""

from __future__ import annotations

import re
from dataclasses import dataclass

CLASS_TO_STATUS = {
    "rejection": "rejected",
    "interview": "interview",
    "assessment": "responded",
    "info_request": "responded",
    "offer": "offer",
    "unknown": None,
}

_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    (
        "rejection",
        re.compile(
            r"unfortunately|not moving forward|other candidates|will not be progressing|"
            r"regret to inform|decided not to|position has been filled",
            re.I,
        ),
        0.85,
    ),
    (
        "offer",
        re.compile(r"\boffer\b|pleased to offer|offer letter|compensation package", re.I),
        0.9,
    ),
    (
        "interview",
        re.compile(
            r"interview|schedule a call|speak with you|phone screen|next step.*meet|"
            r"available.*(monday|tuesday|wednesday|thursday|friday)",
            re.I,
        ),
        0.85,
    ),
    (
        "assessment",
        re.compile(r"assessment|take.?home|coding challenge|hackerrank|test assignment", re.I),
        0.8,
    ),
    (
        "info_request",
        re.compile(
            r"could you (send|provide|share)|additional (info|information)|resume|cv\b", re.I
        ),
        0.7,
    ),
]

_SCAM = [
    (re.compile(r"wire|western union|gift card|crypto|bitcoin", re.I), "payment_request"),
    (re.compile(r"telegram|whatsapp only|signal only", re.I), "chat_only"),
    (re.compile(r"ssn|social security|bank account|routing number", re.I), "sensitive_ask"),
]


@dataclass
class ClassifyResult:
    classification: str
    confidence: float
    citation: str
    scam_level: str
    scam_reasons: list[str]


def classify_reply(*, subject: str, body: str) -> ClassifyResult:
    blob = f"{subject}\n{body}"
    scam_reasons: list[str] = []
    for pat, code in _SCAM:
        if pat.search(blob):
            scam_reasons.append(code)
    scam_level = "red" if scam_reasons else "green"

    for label, pat, conf in _PATTERNS:
        m = pat.search(blob)
        if m:
            return ClassifyResult(
                classification=label,
                confidence=conf,
                citation=m.group(0)[:200],
                scam_level=scam_level,
                scam_reasons=scam_reasons,
            )
    return ClassifyResult(
        classification="unknown",
        confidence=0.2,
        citation=(subject or body[:120])[:200],
        scam_level=scam_level,
        scam_reasons=scam_reasons,
    )
