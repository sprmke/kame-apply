"""Skill strength, years, and last used from the experiences that actually mention a skill.

A skill that only appears in a skills list keeps empty years. We never guess tenure.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from app.taxonomy.aliases import same_skill, skill_key

MAX_MUST = 6
MAX_NICE = 10


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


def _row(exp: Any, key: str) -> Any:
    if isinstance(exp, dict):
        return exp.get(key)
    return getattr(exp, key, None)


def bullet_skills(experience: Any) -> list[str]:
    names: list[str] = []
    for bullet in _row(experience, "bullets") or []:
        for name in (bullet or {}).get("skills") or []:
            text = str(name).strip()
            if text and text not in names:
                names.append(text)
    return names


def _span(experience: Any, today: date) -> tuple[date, date] | None:
    start = _as_date(_row(experience, "start_date"))
    if start is None:
        return None
    end = _as_date(_row(experience, "end_date"))
    if _row(experience, "is_current") or end is None:
        end = today
    if end < start:
        return None
    return start, end


def _merged_months(spans: list[tuple[date, date]]) -> int:
    ordered = sorted(spans)
    if not ordered:
        return 0

    def months(start: date, end: date) -> int:
        return max(0, (end.year - start.year) * 12 + (end.month - start.month))

    total = 0
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += months(current_start, current_end)
            current_start, current_end = start, end
    return total + months(current_start, current_end)


def usage(experiences: Iterable[Any], *, today: date | None = None) -> dict[str, dict[str, Any]]:
    """Per skill: years, last_used year, and the number of mentioning roles."""
    today = today or date.today()
    rows = list(experiences)
    seen: dict[str, dict[str, Any]] = {}
    for exp in rows:
        names = bullet_skills(exp)
        span = _span(exp, today)
        for name in names:
            key = skill_key(name)
            entry = seen.setdefault(
                key,
                {"name": name, "spans": [], "roles": 0, "last_used": None},
            )
            entry["roles"] += 1
            if span is not None:
                entry["spans"].append(span)
                entry["last_used"] = max(entry["last_used"] or 0, span[1].year)
    out: dict[str, dict[str, Any]] = {}
    for key, entry in seen.items():
        months = _merged_months(entry["spans"])
        out[key] = {
            "name": entry["name"],
            "years": round(months / 12, 1) if months else None,
            "last_used": entry["last_used"],
            "roles": entry["roles"],
        }
    return out


def strength(name: str, experiences: Iterable[Any], *, today: date | None = None) -> float:
    rows = list(experiences)
    data = usage(rows, today=today).get(skill_key(name))
    if data is None:
        return 0.0
    score = float(data["roles"])
    years = data.get("years")
    if years:
        score += min(3.0, float(years) * 0.5)
    last_used = data.get("last_used")
    if last_used:
        age = (today or date.today()).year - int(last_used)
        if age <= 2:
            score += 2.0
        elif age <= 5:
            score += 1.0
    return round(score, 2)


def rank(profile_skills: Iterable[str], experiences: Iterable[Any]) -> list[str]:
    rows = list(experiences)
    names = [str(s).strip() for s in profile_skills if str(s).strip()]
    return sorted(names, key=lambda name: -strength(name, rows))


def must_have(
    *,
    profile_skills: Iterable[str],
    role_skills: Iterable[str],
    experiences: Iterable[Any],
    limit: int = MAX_MUST,
) -> list[str]:
    """Always a subset of the person's skills. Empty is better than a filter they cannot meet."""
    rows = list(experiences)
    own = [str(s).strip() for s in profile_skills if str(s).strip()]
    typical = [str(s).strip() for s in role_skills if str(s).strip()]
    if not typical:
        return []
    matched = [name for name in own if any(same_skill(name, role) for role in typical)]
    matched.sort(key=lambda name: -strength(name, rows))
    return matched[:limit]


def nice_to_have(
    *,
    profile_skills: Iterable[str],
    role_skills: Iterable[str],
    must: Iterable[str],
    limit: int = MAX_NICE,
) -> list[str]:
    """Role-typical skills the person may lack. These feed Improve, never a hard filter."""
    own = [str(s).strip() for s in profile_skills if str(s).strip()]
    taken = [str(s).strip() for s in must if str(s).strip()]
    out: list[str] = []
    for raw in role_skills:
        name = str(raw).strip()
        if not name or len(name) > 80:
            continue
        if any(same_skill(name, t) for t in taken):
            continue
        if any(same_skill(name, o) for o in own):
            # A skill the person already has belongs in must, not in gaps.
            continue
        if name.casefold() not in {o.casefold() for o in out}:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def experience_skills(experiences: Iterable[Any]) -> list[str]:
    """Distinct skills mentioned in bullets, in first-seen order."""
    out: list[str] = []
    for exp in experiences:
        for name in bullet_skills(exp):
            if name.casefold() not in {o.casefold() for o in out}:
                out.append(name)
    return out
