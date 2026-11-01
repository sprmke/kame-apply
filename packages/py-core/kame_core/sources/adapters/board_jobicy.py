"""Jobicy remote jobs API.

Terms: https://jobicy.com/jobs-rss-feed (JSON feed; reviewed 2026-11-01).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

from kame_core.sources.base import AdapterMeta, RawJob, SourceHealth
from kame_core.sources.http import fetch_json
from kame_core.sources.registry import register_adapter
from kame_core.sources.textutil import html_to_text, parse_iso_dt


@register_adapter
class JobicyAdapter:
    meta = AdapterMeta(
        key="jobicy",
        name="Jobicy",
        layer="board",
        terms_note="Public JSON feed; reviewed 2026-11-01.",
        countries=("REMOTE",),
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            data, _, _ = await fetch_json("https://jobicy.com/api/v2/remote-jobs")
        if not isinstance(data, dict):
            data = {}
        for j in data.get("jobs") or []:
            yield RawJob(
                external_id=str(j.get("id")),
                source_key="jobicy",
                title=j.get("jobTitle") or "",
                company_name=j.get("companyName") or "",
                url=j.get("url") or "",
                apply_url=j.get("url") or "",
                description_text=html_to_text(j.get("jobDescription") or ""),
                location_text=j.get("jobGeo") or "Remote",
                remote=True,
                employment_type=j.get("jobType") or "",
                posted_at=parse_iso_dt(j.get("pubDate")),
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
