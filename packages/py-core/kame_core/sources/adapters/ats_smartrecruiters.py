"""SmartRecruiters Posting API.

Terms: https://developers.smartrecruiters.com/docs/getting-started (public postings, 2026-11-01).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

from kame_core.sources.adapters._common import require_slug
from kame_core.sources.base import AdapterMeta, RawJob, SourceHealth
from kame_core.sources.http import fetch_json
from kame_core.sources.registry import register_adapter
from kame_core.sources.textutil import name_from_slug, parse_iso_dt


@register_adapter
class SmartRecruitersAdapter:
    meta = AdapterMeta(
        key="smartrecruiters",
        name="SmartRecruiters",
        layer="ats",
        terms_note="Public Posting API; reviewed 2026-11-01.",
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        slug = require_slug(params)
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            data, _, _ = await fetch_json(
                f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
            )
        if not isinstance(data, dict):
            data = {}
        for j in data.get("content") or data.get("postings") or []:
            loc = (
                (j.get("location") or {}).get("city")
                or (j.get("location") or {}).get("region")
                or ""
            )
            yield RawJob(
                external_id=str(j.get("id") or j.get("uuid")),
                source_key="smartrecruiters",
                title=j.get("name") or j.get("title") or "",
                company_name=name_from_slug(slug),
                url=j.get("ref") or j.get("applyUrl") or "",
                apply_url=j.get("applyUrl") or j.get("ref") or "",
                location_text=loc,
                employment_type=(j.get("typeOfEmployment") or {}).get("label") or "",
                ats="smartrecruiters",
                board_slug=slug,
                posted_at=parse_iso_dt(j.get("releasedDate") or j.get("createdOn")),
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
