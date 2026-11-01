"""Workable widget API.

Terms: public careers widget JSON (reviewed 2026-11-01). Link back to apply URL.
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
class WorkableAdapter:
    meta = AdapterMeta(
        key="workable",
        name="Workable",
        layer="ats",
        terms_note="Public widget API; reviewed 2026-11-01.",
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
                f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
            )
            if not isinstance(data, dict):
                data = {}
        company = data.get("name") or name_from_slug(slug)
        for j in data.get("jobs") or []:
            loc = ", ".join(
                x
                for x in [
                    j.get("city"),
                    j.get("country"),
                    "Remote" if j.get("telecommuting") else "",
                ]
                if x
            )
            yield RawJob(
                external_id=str(j.get("shortcode")),
                source_key="workable",
                title=j.get("title") or "",
                company_name=company,
                url=j.get("url") or j.get("shortlink") or "",
                apply_url=j.get("application_url") or j.get("url") or "",
                location_text=loc,
                remote=True if j.get("telecommuting") else None,
                employment_type=j.get("employment_type") or "",
                ats="workable",
                board_slug=slug,
                posted_at=parse_iso_dt(j.get("published_on")),
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
