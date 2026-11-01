"""Normalize RawJob → canonical job fields (pure)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from kame_core.sources.base import RawJob
from kame_core.sources.textutil import html_to_text, sanitize_html

_SENIORITY = [
    (re.compile(r"\bintern\b|\binternship\b", re.I), "intern"),
    (re.compile(r"\bjunior\b|\bjr\.?\b|\bentry[- ]level\b", re.I), "junior"),
    (re.compile(r"\bmid[- ]?level\b|\bintermediate\b", re.I), "mid"),
    (re.compile(r"\bsenior\b|\bsr\.?\b", re.I), "senior"),
    (re.compile(r"\bstaff\b|\bprincipal\b|\blead\b", re.I), "staff"),
    (re.compile(r"\bdirector\b|\bvp\b|\bhead of\b", re.I), "director"),
]

_EMPLOYMENT = [
    (re.compile(r"full[- ]?time|permanent", re.I), "full_time"),
    (re.compile(r"part[- ]?time", re.I), "part_time"),
    (re.compile(r"contract|freelance|temporary", re.I), "contract"),
    (re.compile(r"intern", re.I), "intern"),
]

_REMOTE_ANY = re.compile(r"\b(remote|work from home|wfh|telecommut)\b", re.I)
_REMOTE_US = re.compile(r"remote[^.]{0,40}\b(us|usa|united states)\s*(only|based)?\b", re.I)
_ONSITE = re.compile(r"\b(on[- ]?site|in[- ]office)\b", re.I)
_HYBRID = re.compile(r"\bhybrid\b", re.I)


def normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    t = re.sub(r"[|/].*$", "", t).strip()
    return t[:500]


def infer_seniority(title: str, text: str = "") -> str | None:
    blob = f"{title} {text[:500]}"
    for rx, label in _SENIORITY:
        if rx.search(blob):
            return label
    return None


def infer_employment(raw: str) -> str | None:
    for rx, label in _EMPLOYMENT:
        if rx.search(raw or ""):
            return label
    return None


def parse_remote_eligibility(
    *, location: str, remote_flag: bool | None, text: str
) -> tuple[str | None, dict[str, Any]]:
    blob = f"{location}\n{text[:2000]}"
    if remote_flag is False or (_ONSITE.search(location) and not _REMOTE_ANY.search(blob)):
        return "on_site", {"anywhere": False, "unclear": False}
    if _HYBRID.search(blob):
        return "hybrid", {"anywhere": False, "unclear": False}
    if _REMOTE_US.search(blob):
        return "remote", {
            "anywhere": False,
            "countries": ["US"],
            "unclear": False,
        }
    if remote_flag is True or _REMOTE_ANY.search(blob):
        if re.search(r"anywhere|worldwide|global|unlimited", blob, re.I):
            return "remote", {"anywhere": True, "unclear": False}
        return "remote", {"anywhere": False, "unclear": True}
    if location.strip():
        return "on_site", {"anywhere": False, "unclear": False}
    return None, {"unclear": True}


def content_hash(title: str, company: str, description: str) -> str:
    payload = f"{normalize_title(title)}|{company.strip().lower()}|{re.sub(r'\\s+', ' ', description)[:4000]}"
    return hashlib.sha256(payload.encode()).hexdigest()


def simhash64(text: str) -> int:
    """Simple 64-bit simhash over tokens for fuzzy dedupe (signed int64 for Postgres)."""
    tokens = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    if not tokens:
        return 0
    v = [0] * 64
    for tok in tokens[:2000]:
        h = int(hashlib.md5(tok.encode(), usedforsecurity=False).hexdigest()[:16], 16)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i, x in enumerate(v):
        if x > 0:
            out |= 1 << i
    # Postgres BIGINT is signed; keep value in int64 range.
    out &= (1 << 64) - 1
    if out >= (1 << 63):
        out -= 1 << 64
    return out


def hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def normalize_raw(raw: RawJob) -> dict[str, Any]:
    html = sanitize_html(raw.description_html) if raw.description_html else ""
    text = raw.description_text or html_to_text(html)
    work_mode, eligibility = parse_remote_eligibility(
        location=raw.location_text, remote_flag=raw.remote, text=text
    )
    salary: dict[str, Any] = {}
    if raw.salary_min is not None or raw.salary_text:
        salary = {
            "min": raw.salary_min,
            "max": raw.salary_max,
            "currency": raw.salary_currency,
            "period": raw.salary_period,
            "text": raw.salary_text,
        }
    title = (raw.title or "").strip()
    company = (raw.company_name or "").strip()
    return {
        "title": title,
        "normalized_title": normalize_title(title),
        "company_name": company,
        "seniority": infer_seniority(title, text),
        "employment_type": infer_employment(raw.employment_type) or infer_employment(text[:300]),
        "work_mode": work_mode,
        "locations": [{"place": raw.location_text}] if raw.location_text else [],
        "remote_eligibility": eligibility,
        "salary": salary,
        "description_html": html,
        "description_text": text,
        "content_hash": content_hash(title, company, text),
        "simhash": simhash64(f"{title} {company} {text[:2000]}"),
        "canonical_url": raw.url or raw.apply_url,
        "apply_url": raw.apply_url or raw.url,
        "posted_at": raw.posted_at,
        "expires_at": raw.expires_at,
        "allowed_countries": raw.allowed_countries,
        "ats": raw.ats,
        "board_slug": raw.board_slug,
        "company_domain": raw.company_domain,
        "source_key": raw.source_key,
        "external_id": raw.external_id,
    }
