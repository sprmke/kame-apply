"""Seniority from the latest title and from relevant, non-overlapping years.

Title wins when the two disagree, and the years-based neighbour is added so a search filter never
over-narrows. Everything is pure; dates accept `date`, ISO strings, or None.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

SeniorityLevel = str

_TITLE_LEVELS: tuple[tuple[str, SeniorityLevel], ...] = (
    ("chief", "executive"),
    ("ceo", "executive"),
    ("cto", "executive"),
    ("coo", "executive"),
    ("cfo", "executive"),
    ("managing director", "director"),
    ("vice president", "director"),
    ("vp", "director"),
    ("director", "director"),
    ("head of", "lead"),
    ("head,", "lead"),
    ("supervisor", "lead"),
    ("principal", "principal"),
    ("staff", "staff"),
    ("senior", "senior"),
    ("lead", "lead"),
    ("associate", "junior"),
    ("graduate", "junior"),
    ("entry", "junior"),
    ("junior", "junior"),
    ("manager", "manager"),
    ("trainee", "intern"),
    ("intern", "intern"),
)

_LADDER: tuple[SeniorityLevel, ...] = ("intern", "junior", "mid", "senior", "staff")
_YEARS_FLOOR = {"junior": 0, "mid": 3, "senior": 6, "staff": 10, "principal": 10}


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _row(experience: Any, key: str) -> Any:
    if isinstance(experience, dict):
        return experience.get(key)
    return getattr(experience, key, None)


def _spans(experiences: Iterable[Any], today: date) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    for exp in experiences:
        start = _as_date(_row(exp, "start_date"))
        if start is None:
            continue
        end = _as_date(_row(exp, "end_date"))
        if _row(exp, "is_current") or end is None:
            end = today
        if end < start:
            continue
        out.append((start, end))
    return out


def merged_months(spans: Iterable[tuple[date, date]]) -> int:
    """Months covered by the union of spans, so concurrent roles never double count."""
    ordered = sorted(spans)
    if not ordered:
        return 0
    total = 0
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += _months_between(current_start, current_end)
            current_start, current_end = start, end
    total += _months_between(current_start, current_end)
    return total


def _months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def years_experience(experiences: Iterable[Any], *, today: date | None = None) -> float:
    today = today or date.today()
    return round(merged_months(_spans(experiences, today)) / 12, 1)


def levels_from_title(title: str) -> list[SeniorityLevel]:
    folded = (title or "").casefold()
    out: list[SeniorityLevel] = []
    for word, level in _TITLE_LEVELS:
        if re.search(rf"\b{re.escape(word)}\b", folded) and level not in out:
            out.append(level)
            break
    return out


def level_from_years(years: float) -> SeniorityLevel:
    if years < 1:
        return "intern"
    if years < 3:
        return "junior"
    if years < 6:
        return "mid"
    if years < 10:
        return "senior"
    return "senior"


def _family_tokens(latest_title: str) -> set[str]:
    ignored = {
        "senior",
        "junior",
        "lead",
        "staff",
        "principal",
        "head",
        "of",
        "manager",
        "director",
        "vp",
        "chief",
        "associate",
        "graduate",
        "intern",
        "trainee",
        "the",
        "and",
        "for",
        "ii",
        "iii",
    }
    return {
        token
        for token in (latest_title or "").casefold().replace("-", " ").split()
        if len(token) > 2 and token not in ignored
    }


def relevant_years(
    experiences: Iterable[Any], *, latest_title: str, today: date | None = None
) -> float:
    """Years in roles whose title shares a family word with the latest title."""
    family = _family_tokens(latest_title)
    if not family:
        return years_experience(experiences, today=today)
    relevant = [
        exp
        for exp in experiences
        if family & set((_row(exp, "title") or "").casefold().replace("-", " ").split())
    ]
    if not relevant:
        return 0.0
    return years_experience(relevant, today=today)


def suggest_levels(
    *,
    latest_title: str,
    experiences: Iterable[Any],
    today: date | None = None,
) -> list[SeniorityLevel]:
    """One or two neighbouring levels. Never empty for a person with a role."""
    years = relevant_years(experiences, latest_title=latest_title, today=today)
    by_years = level_from_years(years)
    by_title = levels_from_title(latest_title)
    if not by_title:
        # No level word and no history: leave seniority open rather than guess intern.
        return [by_years] if years > 0 else []
    if by_years in by_title or by_title == ["executive"]:
        return by_title[:2]
    if "intern" in by_title or years <= 0:
        return by_title[:1]
    # Title wins; add the years neighbour so the filter stays wide.
    return [by_title[0], by_years][:2]


def next_level(levels: list[SeniorityLevel]) -> SeniorityLevel | None:
    for level in levels:
        if level in _LADDER:
            index = _LADDER.index(level)
            if index + 1 < len(_LADDER):
                return _LADDER[index + 1]
    return None


def step_up_allowed(
    *,
    latest_title: str,
    experiences: Iterable[Any],
    today: date | None = None,
) -> bool:
    """One step up needs 18 months in the latest role and the years floor for the next level."""
    today = today or date.today()
    levels = suggest_levels(latest_title=latest_title, experiences=experiences, today=today)
    target = next_level(levels)
    if target is None:
        return False
    rows = list(experiences)
    if not rows:
        return False
    latest = rows[0]
    start = _as_date(_row(latest, "start_date"))
    if start is None:
        return False
    end = _as_date(_row(latest, "end_date"))
    if _row(latest, "is_current") or end is None:
        end = today
    if merged_months([(start, end)]) < 18:
        return False
    years = relevant_years(experiences, latest_title=latest_title, today=today)
    return years >= _YEARS_FLOOR.get(target, 0)
