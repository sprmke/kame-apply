"""Industry hook: the field of work a resume points at (multi-industry-support S8).

Deterministic, so setup still works without AI keys. The result is a hint the person
confirms on the review screen; it never switches the workspace by itself.
"""

from __future__ import annotations

from typing import Any

from app.industries.detect import IndustryDetection, detect_industry
from app.industries.packs.general import GENERAL


def detect(reading: Any) -> IndustryDetection | None:
    """Detected field of work, or None when the reading points nowhere useful."""
    parts = [
        str(getattr(reading, "headline", "") or ""),
        str(getattr(reading, "summary", "") or ""),
        str(getattr(reading, "text", "") or ""),
    ]
    text = "\n".join(part for part in parts if part.strip())
    if not text.strip():
        return None
    result = detect_industry(text[:4000])
    if result.pack_key == GENERAL.key:
        return None
    return result
