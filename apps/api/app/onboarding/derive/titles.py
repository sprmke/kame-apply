"""Titles and market synonyms.

Titles are a hard filter in matching, so a proposal always carries synonyms and never an excluded
title. Employer-specific noise is stripped; specialty words that change the job are kept.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

_TRAILING_LEVEL = re.compile(r"\s+(?:i{1,3}|iv|v|\d{1,2})\s*$", re.IGNORECASE)
_AT_COMPANY = re.compile(r"\s+(?:at|@)\s+.+$", re.IGNORECASE)
_SEGMENT_SPLIT = re.compile(r"\s*[,|;]\s*")
_DASH_SPLIT = re.compile(r"\s+[-\u2013\u2014]\s+")
_WHITESPACE = re.compile(r"\s+")

# Words that describe an employer or team, not the job.
_EMPLOYER_NOISE = re.compile(
    r"\b(?:inc|llc|ltd|limited|corp|corporation|gmbh|co|company|group|team|platform|"
    r"payments|products?|division|department)\b",
    re.IGNORECASE,
)
_ROLE_WORD = re.compile(
    r"(engineer|developer|designer|manager|lead|specialist|analyst|assistant|support|"
    r"nurse|teacher|accountant|coordinator|director|consultant|technician|supervisor|"
    r"administrator|officer|scientist|architect|writer|editor|marketer|recruiter|chef|"
    r"cook|barista|driver|clerk|agent|representative|associate|strategist|producer|"
    r"researcher|therapist|pharmacist|electrician|plumber|mechanic|welder|guard|"
    r"receptionist|dispatcher|estimator|inspector|paralegal|attorney|lawyer|auditor)",
    re.IGNORECASE,
)

# Family-level synonyms. Keyed by a substring of the title; generated only when the title matches.
_SYNONYM_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("frontend", ("front end engineer", "ui engineer", "react engineer")),
    ("front end", ("frontend engineer", "ui engineer")),
    ("backend", ("back end engineer", "api engineer", "server engineer")),
    ("back end", ("backend engineer", "api engineer")),
    ("full stack", ("fullstack engineer", "software engineer")),
    ("software engineer", ("software developer", "developer", "programmer")),
    ("data engineer", ("analytics engineer", "data platform engineer")),
    ("data analyst", ("business analyst", "analytics analyst", "reporting analyst")),
    ("product manager", ("product owner", "product lead")),
    ("project manager", ("program manager", "delivery manager")),
    ("customer support", ("customer service", "support specialist", "customer success")),
    ("customer service", ("customer support", "support specialist")),
    ("support lead", ("support manager", "customer support lead")),
    ("qa", ("quality assurance", "test engineer", "qa engineer")),
    ("devops", ("site reliability engineer", "platform engineer", "infrastructure engineer")),
    ("registered nurse", ("staff nurse", "rn")),
    ("nurse", ("registered nurse", "staff nurse")),
    ("accountant", ("accounting associate", "general accountant", "bookkeeper")),
    ("chef", ("cook", "sous chef", "line cook")),
    ("sous chef", ("chef de partie", "head chef", "chef")),
    ("barista", ("coffee barista", "cafe barista")),
    ("server", ("waiter", "waitstaff", "food server")),
    ("warehouse", ("warehouse associate", "warehouse operative")),
    ("electrician", ("electrical technician", "maintenance electrician")),
    ("engineer", ("software engineer", "developer", "engineer")),
)


def clean_title(raw: str) -> str:
    """Drop employer noise and level suffixes, keep the role and its specialty words."""
    text = _AT_COMPANY.sub("", (raw or "").strip())
    text = _DASH_SPLIT.split(text, maxsplit=1)[0]
    segments = _SEGMENT_SPLIT.split(text)
    text = segments[0] if segments else text
    text = _TRAILING_LEVEL.sub("", text)
    text = _WHITESPACE.sub(" ", text).strip(" .-|\u2013\u2014")
    if not text:
        return ""
    # A comma segment that is only employer noise ("Payments Platform") is gone above. A comma
    # segment with a real role word ("Nurse, ICU") keeps the specialty as a parenthetical.
    if len(segments) > 1:
        specialty = segments[1].strip()
        if (
            specialty
            and len(specialty.split()) <= 2
            and not _EMPLOYER_NOISE.search(specialty)
            and specialty.casefold() not in text.casefold()
            and (_ROLE_WORD.search(specialty) or (specialty.isupper() and len(specialty) <= 5))
        ):
            text = f"{text} ({specialty})"
    return text[:120]


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _WHITESPACE.sub(" ", (value or "").strip())
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def synonyms_for(title: str, *, limit: int = 3) -> list[str]:
    folded = (title or "").casefold()
    out: list[str] = []
    for needle, synonyms in _SYNONYM_RULES:
        if needle in folded:
            out.extend(synonyms)
    out = [s for s in _dedupe(out) if s.casefold() != folded]
    if not out and _ROLE_WORD.search(title):
        # A generic variant keeps the filter from excluding a common posting name.
        out = [re.sub(r"\s*\(.*?\)", "", title).strip()]
    return out[:limit]


def headline_title(headline: str) -> str:
    """Use the headline as a title only when it names a role, not a slogan."""
    if not headline or not _ROLE_WORD.search(headline):
        return ""
    return clean_title(headline)


def role_titles(
    *,
    experiences: Iterable[Any],
    headline: str = "",
    limit: int = 2,
    synonym_limit: int = 3,
) -> tuple[list[str], list[str]]:
    """Latest one or two titles plus the headline when it names a role.

    Returns `(titles, synonyms)`. Total titles never exceed five, and nothing is excluded.
    """
    rows = list(experiences)
    titles: list[str] = []
    for exp in rows[:limit]:
        title = exp.get("title") if isinstance(exp, dict) else getattr(exp, "title", "")
        cleaned = clean_title(str(title or ""))
        if cleaned:
            titles.append(cleaned)
    head = headline_title(headline)
    if head:
        titles.append(head)
    titles = _dedupe(titles)[:5]
    synonyms: list[str] = []
    for title in titles:
        synonyms.extend(synonyms_for(title, limit=synonym_limit))
    synonyms = [s for s in _dedupe(synonyms) if s.casefold() not in {t.casefold() for t in titles}]
    return titles, synonyms[:5]


def step_up_title(title: str) -> str:
    clean = clean_title(title)
    folded = clean.casefold()
    if "principal" in folded:
        return clean
    if re.search(r"\bsenior\b", folded):
        return f"Lead {re.sub(r'senior', '', clean, count=1, flags=re.IGNORECASE).strip()}"
    if re.search(r"\blead\b", folded):
        return f"Principal {re.sub(r'lead', '', clean, count=1, flags=re.IGNORECASE).strip()}"
    return f"Senior {clean}"
