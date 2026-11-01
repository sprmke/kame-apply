"""Recruitee offers API.

Terms: public careers API per company subdomain (reviewed 2026-11-01).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

from kame_core.sources.adapters._common import require_slug
from kame_core.sources.base import AdapterMeta, RawJob, SourceHealth
from kame_core.sources.http import fetch_json
from kame_core.sources.registry import register_adapter
from kame_core.sources.textutil import html_to_text, name_from_slug, parse_iso_dt


@register_adapter
class RecruiteeAdapter:
    meta = AdapterMeta(
        key="recruitee",
        name="Recruitee",
        layer="ats",
        terms_note="Public offers API; reviewed 2026-11-01.",
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        slug = require_slug(params)
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            data, _, _ = await fetch_json(f"https://{slug}.recruitee.com/api/offers/")
        if not isinstance(data, dict):
            data = {}
        for j in data.get("offers") or []:
            text = html_to_text(j.get("description") or "")
            yield RawJob(
                external_id=str(j.get("id")),
                source_key="recruitee",
                title=j.get("title") or "",
                company_name=name_from_slug(slug),
                url=j.get("careers_url") or j.get("url") or "",
                apply_url=j.get("careers_url") or j.get("url") or "",
                description_text=text,
                location_text=j.get("location") or "",
                remote=True if j.get("remote") else None,
                employment_type=j.get("employment_type_code") or "",
                ats="recruitee",
                board_slug=slug,
                posted_at=parse_iso_dt(j.get("published_at") or j.get("created_at")),
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
