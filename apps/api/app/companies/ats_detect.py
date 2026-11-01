"""Detect ATS + slug from a careers URL."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    ("greenhouse", re.compile(r"(?:job-)?boards\.greenhouse\.io/([^/?#]+)", re.I), 1),
    ("greenhouse", re.compile(r"boards-api\.greenhouse\.io/v1/boards/([^/?#]+)", re.I), 1),
    ("lever", re.compile(r"jobs\.lever\.co/([^/?#]+)", re.I), 1),
    ("lever", re.compile(r"api(?:\.eu)?\.lever\.co/v0/postings/([^/?#]+)", re.I), 1),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([^/?#]+)", re.I), 1),
    ("ashby", re.compile(r"api\.ashbyhq\.com/posting-api/job-board/([^/?#]+)", re.I), 1),
    ("workable", re.compile(r"apply\.workable\.com/([^/?#]+)", re.I), 1),
    ("smartrecruiters", re.compile(r"jobs\.smartrecruiters\.com/([^/?#]+)", re.I), 1),
    ("smartrecruiters", re.compile(r"careers\.smartrecruiters\.com/([^/?#]+)", re.I), 1),
    ("recruitee", re.compile(r"([a-z0-9-]+)\.recruitee\.com", re.I), 1),
    ("personio", re.compile(r"([a-z0-9-]+)\.jobs\.personio\.(?:de|com)", re.I), 1),
    ("workday", re.compile(r"([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com/.+?/([^/?#]+)", re.I), 2),
    ("bamboohr", re.compile(r"([a-z0-9-]+)\.bamboohr\.com/careers", re.I), 1),
    ("breezy", re.compile(r"([a-z0-9-]+)\.breezy\.hr", re.I), 1),
]


@dataclass(frozen=True, slots=True)
class DetectedBoard:
    ats: str
    slug: str
    url: str


def detect_ats_url(url: str) -> DetectedBoard | None:
    u = (url or "").strip()
    if not u:
        return None
    if not u.startswith("http"):
        u = "https://" + u
    for ats, rx, group in _PATTERNS:
        m = rx.search(u)
        if not m:
            continue
        if ats == "workday" and m.lastindex and m.lastindex >= 2:
            slug = f"{m.group(1)}/{m.group(2)}"
        else:
            slug = m.group(group)
        slug = slug.strip("/").lower()
        if not slug or slug in {"api", "v1", "v0", "jobs"}:
            continue
        return DetectedBoard(ats=ats, slug=slug, url=u)
    return None


def board_public_url(ats: str, slug: str) -> str:
    return {
        "greenhouse": f"https://boards.greenhouse.io/{slug}",
        "lever": f"https://jobs.lever.co/{slug}",
        "ashby": f"https://jobs.ashbyhq.com/{slug}",
        "workable": f"https://apply.workable.com/{slug}",
        "smartrecruiters": f"https://jobs.smartrecruiters.com/{slug}",
        "recruitee": f"https://{slug}.recruitee.com",
        "personio": f"https://{slug}.jobs.personio.com",
        "bamboohr": f"https://{slug}.bamboohr.com/careers",
        "breezy": f"https://{slug}.breezy.hr",
    }.get(ats, f"https://example.com/{ats}/{slug}")
