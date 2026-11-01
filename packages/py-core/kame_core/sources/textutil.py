"""HTML → text and light salary parsing for adapters."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import nh3

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SAL_RE = re.compile(
    r"(?P<cur>\$|USD|EUR|GBP|PHP|AUD|CAD)?\s*(?P<a>\d{2,3}(?:,\d{3})?(?:\.\d+)?|\d+)k?"
    r"(?:\s*[-" + "\u2013\u2014" + r"to]+\s*(?P<b>\d{2,3}(?:,\d{3})?(?:\.\d+)?|\d+)k?)?"
    r"(?:\s*(?P<per>/?\s*(?:year|yr|annum|month|mo|hour|hr)))?",
    re.I,
)


def sanitize_html(html: str) -> str:
    if not html:
        return ""
    return nh3.clean(html, tags=nh3.ALLOWED_TAGS, attributes=nh3.ALLOWED_ATTRIBUTES)


def html_to_text(html: str) -> str:
    if not html:
        return ""
    cleaned = sanitize_html(html)
    text = _TAG_RE.sub(" ", cleaned)
    return _WS_RE.sub(" ", text).strip()


def parse_salary_fragment(text: str) -> dict[str, float | str | None]:
    if not text:
        return {
            "salary_text": "",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": None,
            "salary_period": None,
        }
    m = _SAL_RE.search(text.replace(",", ""))
    if not m:
        return {
            "salary_text": text.strip()[:120],
            "salary_min": None,
            "salary_max": None,
            "salary_currency": None,
            "salary_period": None,
        }

    def num(raw: str | None) -> float | None:
        if not raw:
            return None
        v = float(raw.replace(",", ""))
        if "k" in text[m.start() : m.end()].lower() and v < 1000:
            v *= 1000
        return v

    cur_raw = (m.group("cur") or "").upper()
    currency = {"$": "USD", "USD": "USD", "EUR": "EUR", "GBP": "GBP", "PHP": "PHP"}.get(
        cur_raw, "USD" if cur_raw == "$" else (cur_raw or None)
    )
    per = (m.group("per") or "").lower()
    period = None
    if "hour" in per or "hr" in per:
        period = "hour"
    elif "month" in per or "mo" in per:
        period = "month"
    elif per:
        period = "year"
    return {
        "salary_text": m.group(0).strip(),
        "salary_min": num(m.group("a")),
        "salary_max": num(m.group("b")),
        "salary_currency": currency,
        "salary_period": period,
    }


def parse_iso_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Heuristic: ms vs s
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=UTC)
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


def name_from_slug(slug: str) -> str:
    base = re.sub(r"careers$", "", slug, flags=re.I)
    parts = re.split(r"[-_]+", base)
    return " ".join(p.capitalize() for p in parts if p) or slug
