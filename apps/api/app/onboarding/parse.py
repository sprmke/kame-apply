"""Rule-based resume text reading. No AI, no network, no storage.

Used by `POST /onboarding/plan` so setup never blocks on an AI key (PRD P7). The
output is a draft: the user checks every field before it becomes a profile fact.
Sensitive classes (government IDs, cards, dates of birth, street addresses) are
never returned. Only name, email, headline, location, skills, and years.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

MAX_TEXT = 20_000
_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff\u2060]")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_YEAR = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")
_PLACE = re.compile(
    r"^[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+)*,\s*[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+)*$"
)
_NAME = re.compile(r"^[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3}$")
_ALLCAPS_NAME = re.compile(r"^[A-Z][A-Z.'-]+(?:\s+[A-Z][A-Z.'-]+){1,3}$")
_ROLE_WORDS = re.compile(
    r"(engineer|developer|designer|manager|lead|specialist|analyst|assistant|support|"
    r"nurse|teacher|accountant|coordinator|director|consultant|technician|supervisor|"
    r"administrator|officer|scientist|architect|writer|editor|marketer|recruiter|chef|"
    r"server|barista|driver|clerk|agent|representative|associate|head of)",
    re.I,
)
_SKIP_LINE = re.compile(r"^(resume|curriculum vitae|cv|profile|contact|summary)\b", re.I)


def clean_text(text: str) -> str:
    """Strip control and zero-width characters and cap the length. Never logs the text."""
    out = _ZERO_WIDTH.sub("", text or "")
    out = "".join(ch for ch in out if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return out[:MAX_TEXT]


def _lines(text: str) -> list[str]:
    return [line.strip(" \t-*•|") for line in text.splitlines() if line.strip()]


def _year_span(lines: list[str]) -> int | None:
    years = [int(y) for y in _YEAR.findall("\n".join(lines))]
    years = [y for y in years if 1980 <= y <= datetime.now().year]
    if not years:
        return None
    span = datetime.now().year - min(years)
    return max(1, min(50, span)) if span >= 1 else None


def parse_resume_text(text: str) -> dict[str, Any]:
    """Extract a conservative draft. Missing fields stay missing, never guessed."""
    body = clean_text(text)
    lines = _lines(body)[:120]
    email = (_EMAIL.search(body) or [""])[0] if _EMAIL.search(body) else ""

    head = lines[:18]
    name = ""
    for line in head:
        if _EMAIL.search(line) or _PLACE.match(line) or _SKIP_LINE.match(line):
            continue
        if len(line) <= 48 and (_NAME.match(line) or _ALLCAPS_NAME.match(line)):
            name = line
            break

    headline = ""
    for line in head:
        if line == name or _EMAIL.search(line) or _PLACE.match(line):
            continue
        if len(line) <= 90 and _ROLE_WORDS.search(line) and not _SKIP_LINE.match(line):
            headline = line
            break

    location = ""
    for line in head:
        if _PLACE.match(line) and len(line) <= 80:
            location = line
            break

    skills: list[str] = []
    for i, line in enumerate(lines):
        if re.match(r"^skills?\b", line, re.I):
            raw = re.sub(r"^skills?\s*:?\s*", "", line, flags=re.I)
            if not raw and i + 1 < len(lines):
                raw = lines[i + 1] or ""
            parts = [p.strip() for p in re.split(r"[,;|•/]", raw)]
            skills = [p for p in parts if 1 < len(p) <= 40][:15]
            break

    return {
        "name": name,
        "email": email,
        "headline": headline,
        "location": location,
        "skills": skills,
        "years": _year_span(lines),
    }
