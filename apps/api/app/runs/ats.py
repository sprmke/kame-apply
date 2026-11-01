"""ATS detection from apply URLs (shared by API preflight and runner)."""

from __future__ import annotations

from urllib.parse import urlparse

# Host fragments → adapter key. Order matters for overlapping hosts.
_HOST_MAP: list[tuple[str, str]] = [
    ("boards.greenhouse.io", "greenhouse"),
    ("job-boards.greenhouse.io", "greenhouse"),
    ("greenhouse.io", "greenhouse"),
    ("jobs.lever.co", "lever"),
    ("lever.co", "lever"),
    ("jobs.ashbyhq.com", "ashby"),
    ("ashbyhq.com", "ashby"),
    ("apply.workable.com", "workable"),
    ("workable.com", "workable"),
    ("jobs.smartrecruiters.com", "smartrecruiters"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("myworkdayjobs.com", "workday"),
    ("workday.com", "workday"),
    ("icims.com", "icims"),
    ("successfactors", "successfactors"),
    ("linkedin.com", "linkedin"),
    ("indeed.com", "indeed"),
    ("jobstreet.", "jobstreet"),
]


def detect_ats(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    path = (urlparse(url).path or "").lower()
    blob = f"{host}{path}"
    for needle, ats in _HOST_MAP:
        if needle in blob:
            return ats
    return "generic"


# Platforms that must never auto-submit (PRD P3 / job-site-access).
NO_AUTO_SUBMIT = frozenset({"linkedin", "indeed", "jobstreet", "seek"})
