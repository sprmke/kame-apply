"""The Muse jobs API (public).

Terms: https://www.themuse.com/developers/api/v2 (reviewed 2026-11-01).
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
class MuseAdapter:
    meta = AdapterMeta(
        key="muse",
        name="The Muse",
        layer="board",
        terms_note="Public API v2; reviewed 2026-11-01.",
        countries=("US",),
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            page = int(params.get("page") or 1)
            data, _, _ = await fetch_json(f"https://www.themuse.com/api/public/jobs?page={page}")
        if not isinstance(data, dict):
            data = {}
        for j in data.get("results") or []:
            locs = [loc.get("name") for loc in (j.get("locations") or []) if loc.get("name")]
            comps = j.get("company") or {}
            yield RawJob(
                external_id=str(j.get("id")),
                source_key="muse",
                title=j.get("name") or "",
                company_name=comps.get("name") or "",
                url=j.get("refs", {}).get("landing_page") or "",
                apply_url=j.get("refs", {}).get("landing_page") or "",
                description_text=html_to_text(j.get("contents") or ""),
                location_text=", ".join(locs),
                remote=any(
                    "flexible" in (x or "").lower() or "remote" in (x or "").lower() for x in locs
                )
                or None,
                posted_at=parse_iso_dt(j.get("publication_date")),
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
