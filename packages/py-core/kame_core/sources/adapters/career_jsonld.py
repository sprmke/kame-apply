"""Generic career-page JSON-LD JobPosting extractor (Layer 3).

Terms: only public pages; robots.txt respected by caller; reviewed 2026-11-01.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

import httpx

from kame_core.sources.base import AdapterMeta, RawJob, SourceHealth
from kame_core.sources.http import BlockSignalError, fetch_json, robots_allowed
from kame_core.sources.registry import register_adapter
from kame_core.sources.textutil import html_to_text, parse_iso_dt

_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)


def extract_job_postings(html: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in _LD_RE.finditer(html or ""):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@graph"):
                items.extend(item["@graph"])
                continue
            t = item.get("@type") if isinstance(item, dict) else None
            types = t if isinstance(t, list) else [t]
            if "JobPosting" in types:
                out.append(item)
    return out


@register_adapter
class CareerJsonLdAdapter:
    meta = AdapterMeta(
        key="career_jsonld",
        name="Career page JSON-LD",
        layer="career_page",
        terms_note="Structured JobPosting on public career pages; robots.txt required. Reviewed 2026-11-01.",
        rate_limit_per_minute=10,
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        if self._fixture_dir:
            html = (self._fixture_dir / "page.html").read_text(encoding="utf-8")
            url = "https://example.com/careers"
        else:
            url = str(params.get("url") or "").strip()
            if not url:
                raise ValueError("url is required")
            if not await robots_allowed(url):
                host = httpx.URL(url).host or "unknown"
                raise BlockSignalError(0, host, "robots_disallow")
            html, _, _ = await fetch_json(url, headers={"Accept": "text/html"})
            if not isinstance(html, str):
                html = str(html)
        for j in extract_job_postings(html):
            org = j.get("hiringOrganization") or {}
            if isinstance(org, list):
                org = org[0] if org else {}
            loc = j.get("jobLocation") or {}
            if isinstance(loc, list):
                loc = loc[0] if loc else {}
            addr = (loc.get("address") if isinstance(loc, dict) else None) or {}
            if isinstance(addr, list):
                addr = addr[0] if addr else {}
            location = ", ".join(
                str(x)
                for x in [
                    addr.get("addressLocality") if isinstance(addr, dict) else None,
                    addr.get("addressRegion") if isinstance(addr, dict) else None,
                    addr.get("addressCountry") if isinstance(addr, dict) else None,
                ]
                if x
            )
            remote = None
            if j.get("jobLocationType") == "TELECOMMUTE":
                remote = True
            desc = j.get("description") or ""
            yield RawJob(
                external_id=str(j.get("identifier") or j.get("url") or j.get("title")),
                source_key="career_jsonld",
                title=j.get("title") or "",
                company_name=(org.get("name") if isinstance(org, dict) else "") or "",
                url=j.get("url") or url,
                apply_url=j.get("url") or url,
                description_html=desc if "<" in str(desc) else "",
                description_text=html_to_text(desc) if "<" in str(desc) else str(desc),
                location_text=location,
                remote=remote,
                employment_type=str(j.get("employmentType") or ""),
                posted_at=parse_iso_dt(j.get("datePosted")),
                expires_at=parse_iso_dt(j.get("validThrough")),
                company_domain=(org.get("sameAs") if isinstance(org, dict) else None),
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
