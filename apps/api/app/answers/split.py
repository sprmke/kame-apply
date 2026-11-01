"""Split pasted form text into questions and detect constraints."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_NUM_SPLIT = re.compile(
    r"(?:^|\n)\s*(?:\(?\d{1,2}\)?[.)]|[Qq](?:uestion)?\s*\d{1,2}[:.)]|[-•*])\s+"
)
_CHAR_LIMIT = re.compile(
    r"(?i)(?:max(?:imum)?|up to|limit(?:ed)?(?:\s+to)?|no more than)\s*[:\-]?\s*(\d{2,5})\s*(?:char(?:acter)?s?|字)?"
)
_YES_NO = re.compile(r"(?i)\b(yes\s*/\s*no|y/n|true\s*/\s*false)\b")
_NUMBER = re.compile(r"(?i)\b(enter a number|numeric only|how many|years of experience)\b")
_DATE = re.compile(r"(?i)\b(date|mm/dd/yyyy|yyyy-mm-dd|start date|available from)\b")
_SELECT = re.compile(r"(?i)(?:options?|choose one|select one)\s*[:\-]\s*(.+)$")
_LEGAL = re.compile(
    r"(?i)\b(age|date of birth|religion|marital status|married|pregnant|"
    r"disability|sexual orientation|political affiliation)\b"
)


@dataclass
class SplitQuestion:
    text: str
    char_limit: int | None = None
    format: str = "text"  # text | yes_no | number | date | select
    options: list[str] = field(default_factory=list)
    legal_flag: bool = False
    constraints: dict[str, Any] = field(default_factory=dict)


def _detect_constraints(q: str) -> SplitQuestion:
    fmt = "text"
    options: list[str] = []
    limit = None
    m = _CHAR_LIMIT.search(q)
    if m:
        limit = int(m.group(1))
    if _YES_NO.search(q):
        fmt = "yes_no"
    elif _DATE.search(q) and "?" in q:
        fmt = "date"
    elif _NUMBER.search(q):
        fmt = "number"
    sm = _SELECT.search(q)
    if sm:
        fmt = "select"
        raw = sm.group(1)
        options = [p.strip(" .;") for p in re.split(r"[,|/]| or ", raw) if p.strip()]
        options = [o for o in options if 1 < len(o) < 80][:12]
    legal = bool(_LEGAL.search(q))
    return SplitQuestion(
        text=q.strip(),
        char_limit=limit,
        format=fmt,
        options=options,
        legal_flag=legal,
        constraints={
            "char_limit": limit,
            "format": fmt,
            "options": options,
            "legal_flag": legal,
        },
    )


def split_questions(raw: str) -> list[SplitQuestion]:
    text = (raw or "").strip()
    if not text:
        return []

    # Prefer numbered / bullet splits
    parts = [p.strip() for p in _NUM_SPLIT.split(text) if p and p.strip()]
    if len(parts) >= 2:
        # drop empty lead if split ate the first marker
        out = [_detect_constraints(p) for p in parts if len(p) > 3]
        if len(out) >= 2:
            return out

    # Blank-line paragraphs that look like questions
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if len(paras) >= 2:
        qs = [p for p in paras if "?" in p or len(p) < 280]
        if len(qs) >= 2:
            return [_detect_constraints(p) for p in qs]

    # Single lines ending with ?
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    qlines = [ln for ln in lines if ln.endswith("?") or _CHAR_LIMIT.search(ln)]
    if len(qlines) >= 2:
        return [_detect_constraints(p) for p in qlines]

    return [_detect_constraints(text)]
