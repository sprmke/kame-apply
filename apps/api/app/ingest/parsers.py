"""Template parsers for job-alert emails (LinkedIn, Indeed, JobStreet, …)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from email import message_from_bytes
from email.message import Message
from html import unescape
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class ParsedJob:
    title: str
    company: str
    location: str
    url: str
    confidence: float
    provider: str


@dataclass
class ParseResult:
    provider: str
    jobs: list[ParsedJob]
    confidence: float
    kind: str  # alert | forward_confirm | unknown
    notes: list[str]


def _strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", unescape(text)).strip()


def _links(html: str) -> list[str]:
    return [unescape(m) for m in _HREF_RE.findall(html or "")]


def detect_provider(sender: str, subject: str) -> str:
    blob = f"{sender} {subject}".lower()
    if "linkedin" in blob:
        return "linkedin"
    if "indeed" in blob:
        return "indeed"
    if "jobstreet" in blob or "seek.com" in blob or "@seek." in blob:
        return "jobstreet"
    if "glassdoor" in blob:
        return "glassdoor"
    if "kalibrr" in blob:
        return "kalibrr"
    if "googlealerts" in blob or ("google.com" in blob and "alert" in blob):
        return "google_alerts"
    return "generic"


def is_forward_confirm(subject: str, text: str) -> bool:
    low = f"{subject} {text}".lower()
    return any(
        x in low
        for x in (
            "confirm that you want to forward",
            "confirmation code",
            "verify forwarding",
            "forwarding confirmation",
            "please confirm your forwarding",
        )
    )


def unwrap_tracking_url(url: str) -> str:
    """Best-effort unwrap of common redirect/tracking wrappers (no network)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return url
    host = (parsed.hostname or "").lower()
    qs = parse_qs(parsed.query)
    for key in ("url", "u", "q", "dest", "redirect", "redirect_url", "target"):
        if qs.get(key):
            candidate = unquote(qs[key][0])
            if candidate.startswith("http"):
                return candidate
    # LinkedIn /lnkd.in style path sometimes embeds destination in query
    if "linkedin.com" in host and "url" in qs:
        return unquote(qs["url"][0])
    return url


def _job_from_parts(
    *, title: str, company: str, location: str, url: str, provider: str, confidence: float
) -> ParsedJob | None:
    title = _WS_RE.sub(" ", title).strip()
    company = _WS_RE.sub(" ", company).strip()
    location = _WS_RE.sub(" ", location).strip()
    url = unwrap_tracking_url(url.strip())
    if not title or not url.startswith("http"):
        return None
    return ParsedJob(
        title=title[:300],
        company=company[:200] or "Unknown",
        location=location[:200],
        url=url[:2000],
        confidence=confidence,
        provider=provider,
    )


def _parse_linkedin(html: str, text: str) -> list[ParsedJob]:
    jobs: list[ParsedJob] = []
    # Pattern: Title at Company · Location with job link
    for m in re.finditer(
        r"(?P<title>[^\n|]{3,120}?)\s+(?:at|@)\s+(?P<company>[^\n|]{2,80}?)"
        r"(?:\s*[·|]\s*(?P<loc>[^\n]{2,80}))?",
        text,
        re.I,
    ):
        # Find nearest linkedin job link
        url = next(
            (
                u
                for u in _links(html)
                if "linkedin.com/jobs" in u.lower() or "/jobs/view/" in u.lower()
            ),
            "",
        )
        if not url:
            continue
        job = _job_from_parts(
            title=m.group("title"),
            company=m.group("company"),
            location=m.group("loc") or "",
            url=url,
            provider="linkedin",
            confidence=0.9,
        )
        if job:
            jobs.append(job)
    # Fallback: one job card per jobs/view link
    if not jobs:
        for u in _links(html):
            if "/jobs/view/" not in u.lower() and "linkedin.com/jobs" not in u.lower():
                continue
            # Title often in surrounding text near link label — use subject-ish snippet
            job = _job_from_parts(
                title="LinkedIn job",
                company="Unknown",
                location="",
                url=u,
                provider="linkedin",
                confidence=0.55,
            )
            if job:
                jobs.append(job)
    return _dedupe(jobs)


def _parse_indeed(html: str, text: str) -> list[ParsedJob]:
    jobs: list[ParsedJob] = []
    for m in re.finditer(
        r"(?P<title>[^\n]{3,120})\s+-\s+(?P<company>[^\n]{2,80})"
        r"(?:\s+-\s+(?P<loc>[^\n]{2,80}))?",
        text,
    ):
        url = next((u for u in _links(html) if "indeed." in u.lower()), "")
        job = _job_from_parts(
            title=m.group("title"),
            company=m.group("company"),
            location=m.group("loc") or "",
            url=url or next(iter(_links(html)), ""),
            provider="indeed",
            confidence=0.88,
        )
        if job:
            jobs.append(job)
    if not jobs:
        for u in _links(html):
            if "indeed." not in u.lower() or (
                "/rc/clk" not in u.lower() and "/viewjob" not in u.lower()
            ):
                if "indeed." not in u.lower():
                    continue
            job = _job_from_parts(
                title="Indeed job",
                company="Unknown",
                location="",
                url=u,
                provider="indeed",
                confidence=0.5,
            )
            if job:
                jobs.append(job)
    return _dedupe(jobs)


def _parse_jobstreet(html: str, text: str) -> list[ParsedJob]:
    jobs: list[ParsedJob] = []
    for m in re.finditer(
        r"(?P<title>[^\n]{3,120})\s+at\s+(?P<company>[^\n]{2,80})",
        text,
        re.I,
    ):
        url = next(
            (u for u in _links(html) if "jobstreet." in u.lower() or "seek.com" in u.lower()),
            "",
        )
        job = _job_from_parts(
            title=m.group("title"),
            company=m.group("company"),
            location="",
            url=url or next(iter(_links(html)), ""),
            provider="jobstreet",
            confidence=0.85,
        )
        if job:
            jobs.append(job)
    return _dedupe(jobs)


def _parse_glassdoor(html: str, text: str) -> list[ParsedJob]:
    jobs: list[ParsedJob] = []
    for u in _links(html):
        if "glassdoor." not in u.lower() or (
            "job-listing" not in u.lower() and "/job/" not in u.lower()
        ):
            if "glassdoor." not in u.lower():
                continue
        job = _job_from_parts(
            title="Glassdoor job",
            company="Unknown",
            location="",
            url=u,
            provider="glassdoor",
            confidence=0.55,
        )
        if job:
            jobs.append(job)
    for m in re.finditer(r"(?P<title>[^\n]{3,100})\s+-\s+(?P<company>[^\n]{2,60})", text):
        if jobs:
            jobs[0].title = m.group("title").strip()
            jobs[0].company = m.group("company").strip()
            jobs[0].confidence = 0.8
            break
    return _dedupe(jobs)


def _parse_kalibrr(html: str, _text: str) -> list[ParsedJob]:
    jobs: list[ParsedJob] = []
    for u in _links(html):
        if "kalibrr." not in u.lower():
            continue
        job = _job_from_parts(
            title="Kalibrr job",
            company="Unknown",
            location="",
            url=u,
            provider="kalibrr",
            confidence=0.6,
        )
        if job:
            jobs.append(job)
    return _dedupe(jobs)


def _parse_google_alerts(html: str, text: str) -> list[ParsedJob]:
    jobs: list[ParsedJob] = []
    for u in _links(html):
        if "google.com/url" in u or u.startswith("http"):
            dest = unwrap_tracking_url(u)
            host = (urlparse(dest).hostname or "").lower()
            if "google." in host:
                continue
            # Title: first line-ish near link
            title = text.split("\n")[0][:120] if text else "Alert"
            job = _job_from_parts(
                title=title or "Google Alert",
                company="Unknown",
                location="",
                url=dest,
                provider="google_alerts",
                confidence=0.5,
            )
            if job:
                jobs.append(job)
    return _dedupe(jobs)[:20]


def _parse_generic(html: str, text: str) -> list[ParsedJob]:
    jobs: list[ParsedJob] = []
    for u in _links(html):
        low = u.lower()
        if not any(
            x in low
            for x in (
                "job",
                "career",
                "greenhouse",
                "lever.co",
                "ashby",
                "workday",
                "smartrecruiters",
            )
        ):
            continue
        job = _job_from_parts(
            title=(text.split("\n")[0][:120] if text else "Job"),
            company="Unknown",
            location="",
            url=u,
            provider="generic",
            confidence=0.4,
        )
        if job:
            jobs.append(job)
    return _dedupe(jobs)[:25]


def _dedupe(jobs: list[ParsedJob]) -> list[ParsedJob]:
    seen: set[str] = set()
    out: list[ParsedJob] = []
    for j in jobs:
        key = j.url.split("?")[0].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out


_PARSERS = {
    "linkedin": _parse_linkedin,
    "indeed": _parse_indeed,
    "jobstreet": _parse_jobstreet,
    "glassdoor": _parse_glassdoor,
    "kalibrr": _parse_kalibrr,
    "google_alerts": _parse_google_alerts,
    "generic": _parse_generic,
}


def parse_mime(raw: bytes, *, sender: str = "", subject: str = "") -> ParseResult:
    msg: Message = message_from_bytes(raw)
    sender = sender or str(msg.get("From") or "")
    subject = subject or str(msg.get("Subject") or "")
    html = ""
    text = ""

    def _part_text(part: Message) -> str:
        raw_payload = part.get_payload(decode=True)
        if not isinstance(raw_payload, (bytes, bytearray)):
            data = part.get_payload()
            return str(data or "")
        charset = part.get_content_charset() or "utf-8"
        return bytes(raw_payload).decode(charset, errors="replace")

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            try:
                body = _part_text(part)
            except Exception:  # noqa: S112 — skip bad MIME parts
                continue
            if ctype == "text/html" and not html:
                html = body
            elif ctype == "text/plain" and not text:
                text = body
    else:
        body = _part_text(msg)
        if msg.get_content_type() == "text/html":
            html = body
        else:
            text = body
    if not text and html:
        text = _strip_html(html)

    if is_forward_confirm(subject, text):
        return ParseResult(
            provider=detect_provider(sender, subject),
            jobs=[],
            confidence=1.0,
            kind="forward_confirm",
            notes=["Forwarding confirmation"],
        )

    provider = detect_provider(sender, subject)
    parser = _PARSERS.get(provider, _parse_generic)
    jobs = parser(html, text)
    if not jobs and provider != "generic":
        jobs = _parse_generic(html, text)
        provider = "generic"
    conf = max((j.confidence for j in jobs), default=0.0)
    if jobs and conf < 0.6:
        kind = "unknown"
    else:
        kind = "alert" if jobs else "unknown"
    return ParseResult(
        provider=provider,
        jobs=jobs,
        confidence=conf,
        kind=kind,
        notes=[],
    )


def jobs_to_dicts(jobs: list[ParsedJob]) -> list[dict[str, Any]]:
    return [
        {
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "url": j.url,
            "confidence": j.confidence,
            "provider": j.provider,
            "external_id": hashlib.sha256(j.url.encode()).hexdigest()[:24],
        }
        for j in jobs
    ]
