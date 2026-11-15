"""Writing style preset from the role, never from the person's name or country."""

from __future__ import annotations

FORMAL_MARKERS = (
    "legal",
    "lawyer",
    "attorney",
    "paralegal",
    "finance",
    "financial",
    "accounting",
    "audit",
    "banking",
    "compliance",
    "regulatory",
    "government",
    "public sector",
    "policy",
    "healthcare administration",
    "hospital administration",
    "clinical governance",
)


def preset_for(*, headline: str = "", levels: list[str] | None = None) -> str:
    folded = (headline or "").casefold()
    if any(marker in folded for marker in FORMAL_MARKERS):
        return "formal"
    if any(level in {"director", "executive"} for level in (levels or [])):
        return "formal"
    return "plain"
