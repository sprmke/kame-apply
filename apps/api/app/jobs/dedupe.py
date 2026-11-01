"""Job dedupe: exact external id, then fuzzy company+title+simhash."""

from __future__ import annotations

from dataclasses import dataclass

from app.jobs.normalize import hamming64, normalize_title

# Tuned for precision-first (target ≥98% precision on labeled pairs).
TITLE_EQUAL = True
SIMHASH_MAX_DISTANCE = 8


@dataclass(frozen=True, slots=True)
class DedupeKey:
    company_norm: str
    title_norm: str
    simhash: int


def company_norm(name: str) -> str:
    return " ".join((name or "").lower().split())


def same_job(
    *,
    company_a: str,
    title_a: str,
    simhash_a: int,
    company_b: str,
    title_b: str,
    simhash_b: int,
) -> bool:
    if company_norm(company_a) != company_norm(company_b):
        return False
    if normalize_title(title_a) != normalize_title(title_b):
        return False
    return hamming64(simhash_a or 0, simhash_b or 0) <= SIMHASH_MAX_DISTANCE


_ATS_RANK = {
    "greenhouse": 100,
    "lever": 95,
    "ashby": 95,
    "workable": 90,
    "smartrecruiters": 85,
    "recruitee": 85,
    "personio": 80,
    "workday": 80,
    "bamboohr": 70,
    "breezy": 70,
    "career_jsonld": 60,
    "remotive": 40,
    "remoteok": 40,
    "himalayas": 40,
    "arbeitnow": 40,
    "jobicy": 40,
    "muse": 40,
}


def prefer_apply_url(candidates: list[tuple[str, str]]) -> str:
    """candidates: list of (source_key, url). Prefer company ATS."""
    if not candidates:
        return ""
    ranked = sorted(candidates, key=lambda c: _ATS_RANK.get(c[0], 10), reverse=True)
    return ranked[0][1]
