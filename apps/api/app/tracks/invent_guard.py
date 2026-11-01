"""Post-check: NL compiler may only set fields that the text mentions.

Heuristic token/keyword overlap — not a second LLM call. Clear false positives
are acceptable; silent invented salary/visa/caps are not.
"""

from __future__ import annotations

import re
from typing import Any

from app.tracks.merge import CriteriaPatch

_FIELD_CUES: dict[str, tuple[str, ...]] = {
    "titles": ("title", "role", "engineer", "nurse", "manager", "developer", "designer"),
    "occupations": ("occupation", "isco", "esco", "o*net", "onet"),
    "skills": ("skill", "must", "nice", "exclude", "stack", "python", "kubernetes", "typescript"),
    "seniority": (
        "junior",
        "mid",
        "senior",
        "staff",
        "principal",
        "lead",
        "intern",
        "director",
        "executive",
        "manager",
    ),
    "employment_types": (
        "full-time",
        "full time",
        "part-time",
        "contract",
        "freelance",
        "internship",
        "temporary",
    ),
    "work_modes": ("remote", "hybrid", "on-site", "onsite", "office"),
    "remote_eligibility": (
        "timezone",
        "worldwide",
        "anywhere",
        "apac",
        "latam",
        "eu",
        "eligible",
        "from ",
    ),
    "locations": (
        "in ",
        "based",
        "city",
        "singapore",
        "dubai",
        "berlin",
        "london",
        "manila",
        "km",
        "radius",
    ),
    "visa_sponsorship": ("visa", "sponsorship", "sponsor"),
    "relocation": ("relocation", "relocate"),
    "salary": ("salary", "$", "usd", "eur", "gbp", "php", "aed", "/month", "/year", "pay"),
    "companies": ("company", "companies", "agency", "agencies", "startup", "industry", "crypto"),
    "posting_max_age_days": ("posted", "days old", "last week", "fresh", "age"),
    "languages": ("language", "english", "french", "german", "spanish", "mandarin"),
    "education": ("degree", "bachelor", "master", "phd", "education", "diploma"),
    "clearance": ("clearance", "security clearance", "secret", "nv1"),
    "keywords": ("keyword", "boolean", "must mention"),
    "min_match_score": ("match score", "minimum score"),
    "caps": ("per day", "cap", "maximum applications"),
}


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def invented_fields(text: str, patch: CriteriaPatch) -> list[str]:
    """Return patch field names that look invented relative to `text`."""
    body = _fold(text)
    dumped = patch.model_dump(mode="json", exclude_none=True)
    invented: list[str] = []
    for key, value in dumped.items():
        if key in ("replace_paths", "removals"):
            continue
        if _is_empty(value):
            continue
        cues = _FIELD_CUES.get(key, ())
        if not cues:
            continue
        # Also accept literal values from the patch appearing in the text.
        literals = _literals(key, value)
        if any(c in body for c in cues) or any(_fold(lit) in body for lit in literals if lit):
            continue
        invented.append(key)
    return invented


def strip_invented(patch: CriteriaPatch, invented: list[str]) -> CriteriaPatch:
    if not invented:
        return patch
    data = patch.model_dump(mode="json")
    for key in invented:
        data[key] = None
    return CriteriaPatch.model_validate({k: v for k, v in data.items() if v is not None})


def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, (list, dict, str)) and len(v) == 0:
        return True
    if isinstance(v, dict):
        return all(_is_empty(x) for x in v.values())
    return False


def _literals(key: str, value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                for k in ("title", "place", "code", "label"):
                    if item.get(k):
                        out.append(str(item[k]))
                for syn in item.get("synonyms") or []:
                    out.append(str(syn))
    elif isinstance(value, dict):
        for _k, v in value.items():
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, list):
                out.extend(str(x) for x in v if isinstance(x, (str, int, float)))
            elif isinstance(v, (int, float, bool)):
                out.append(str(v))
    elif isinstance(value, (str, int, float, bool)):
        out.append(str(value))
    return out
