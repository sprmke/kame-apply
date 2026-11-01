"""Deterministic entity matching for resume merge (no LLM).

Matches by normalized names + fuzzy similarity + date overlap. Used by the merge preview
to classify draft items as identical, conflicting, or new.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

# Drop legal suffixes so "Acme Corp" and "Acme Corporation" collapse to the same token.
_ORG_SUFFIX = re.compile(
    r"\b(incorporated|corporation|company|limited|llc|ltd|inc|corp|co|plc)\b\.?",
    re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9\s]+")
_SPACES = re.compile(r"\s+")

COMPANY_MATCH = 0.88
TITLE_MATCH = 0.80
NAME_MATCH = 0.88
BULLET_MATCH = 0.90
FAR_FUTURE = date(9999, 12, 31)
FAR_PAST = date(1900, 1, 1)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.casefold().strip()
    text = _NON_ALNUM.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def normalize_org(value: str | None) -> str:
    text = normalize_text(value)
    text = _ORG_SUFFIX.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def similarity(a: str | None, b: str | None, *, org: bool = False) -> float:
    left = normalize_org(a) if org else normalize_text(a)
    right = normalize_org(b) if org else normalize_text(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    ratio = SequenceMatcher(None, left, right).ratio()
    if org:
        # "St. Luke's" vs "St. Luke's Medical Center": containment beats raw ratio.
        shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
        if len(shorter) >= 6 and shorter in longer:
            return max(ratio, 0.92)
        left_tokens, right_tokens = set(left.split()), set(right.split())
        if left_tokens and right_tokens:
            overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
            if overlap >= 0.6 and len(left_tokens & right_tokens) >= 2:
                return max(ratio, 0.88)
    return ratio


def _end(end: date | None, is_current: bool) -> date:
    if is_current or end is None:
        return FAR_FUTURE
    return end


def dates_overlap(
    a_start: date | None,
    a_end: date | None,
    a_current: bool,
    b_start: date | None,
    b_end: date | None,
    b_current: bool,
) -> bool:
    """True when ranges overlap, or when both sides lack any date anchors."""
    a_has = a_start is not None or a_end is not None or a_current
    b_has = b_start is not None or b_end is not None or b_current
    if not a_has and not b_has:
        return True
    if not a_has or not b_has:
        # One side has dates, the other doesn't: still allow a name match to proceed,
        # but treat as overlapping so the user can resolve date fills.
        return True
    a_lo = a_start or FAR_PAST
    b_lo = b_start or FAR_PAST
    a_hi = _end(a_end, a_current)
    b_hi = _end(b_end, b_current)
    return a_lo <= b_hi and b_lo <= a_hi


@dataclass(frozen=True)
class ExperienceMatchScore:
    company: float
    title: float
    dates: bool
    score: float

    @property
    def is_match(self) -> bool:
        return (
            self.company >= COMPANY_MATCH
            and self.title >= TITLE_MATCH
            and self.dates
            and self.score >= 0.82
        )


def score_experience(
    *,
    company_a: str,
    title_a: str,
    start_a: date | None,
    end_a: date | None,
    current_a: bool,
    company_b: str,
    title_b: str,
    start_b: date | None,
    end_b: date | None,
    current_b: bool,
) -> ExperienceMatchScore:
    company = similarity(company_a, company_b, org=True)
    title = similarity(title_a, title_b)
    dates = dates_overlap(start_a, end_a, current_a, start_b, end_b, current_b)
    # Weighted blend; dates are a gate via is_match, not the score alone.
    score = 0.55 * company + 0.45 * title
    return ExperienceMatchScore(company=company, title=title, dates=dates, score=score)


def score_named(a: str | None, b: str | None, *, org: bool = False) -> float:
    return similarity(a, b, org=org)


def bullets_equivalent(a: str, b: str) -> bool:
    return similarity(a, b) >= BULLET_MATCH


def json_safe(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value
