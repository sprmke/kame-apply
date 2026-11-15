"""Evidence check: a claim survives only when its quote exists in the resume text.

Normalization handles case, whitespace, bullets, and common PDF ligatures. A dropped claim is
never replaced or repaired; it disappears from the review.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from app.onboarding import schemas as s

_LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
}
_BULLET = re.compile(r"^[\s\-\u2022\u00b7*\u25aa\u25cf|]+")
_SPACE = re.compile(r"\s+")

# Profile header fields that are settings, not claims about the person.
_SETTING_TARGETS = frozenset({"profile.timezone", "profile.language"})
_PROFILE_SETTINGS_GROUPS = frozenset({"account", "writing", "studio", "searches", "industry"})


def normalize(text: str) -> str:
    out = text or ""
    for source, target in _LIGATURES.items():
        out = out.replace(source, target)
    out = _BULLET.sub("", out)
    return _SPACE.sub(" ", out).strip().casefold()


def quote_found(text: str, quote: str) -> bool:
    needle = normalize(quote)
    return bool(needle) and needle in normalize(text)


def _claim(item: s.SetupItem) -> bool:
    if item.needs_you or item.group in _PROFILE_SETTINGS_GROUPS:
        return False
    if item.group in {"profile", "answers"}:
        return True
    return False


def _source_allowed(item: s.SetupItem) -> bool:
    if not _claim(item):
        return True
    if item.source in {"resume", "you_said"}:
        return True
    if item.group == "answers":
        # Recommended defaults are allowed but never approved (checked at build time).
        return True
    return item.target in _SETTING_TARGETS


def ground_items(items: Iterable[s.SetupItem], text: str) -> tuple[list[s.SetupItem], int]:
    kept: list[s.SetupItem] = []
    dropped = 0
    for item in items:
        if not _source_allowed(item):
            dropped += 1
            continue
        if item.source == "resume" and _claim(item):
            quotes = [ref.quote for ref in item.evidence if ref.quote]
            if not quotes or not all(quote_found(text, quote) for quote in quotes):
                dropped += 1
                continue
        kept.append(item)
    return kept, dropped


def _counts(items: list[s.SetupItem], searches: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.group] = counts.get(item.group, 0) + 1
    counts["searches"] = len(searches)
    counts["needs_you"] = sum(1 for item in items if item.needs_you)
    return counts


def ground_bundle(bundle: s.SetupBundle, text: str) -> tuple[s.SetupBundle, int]:
    items, dropped = ground_items(bundle.items, text)
    if dropped == 0:
        return bundle, 0
    return (
        bundle.model_copy(update={"items": items, "counts": _counts(items, list(bundle.searches))}),
        dropped,
    )
