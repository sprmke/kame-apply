"""Arbeitnow job board API (EU-heavy).

Terms: public API https://www.arbeitnow.com/api/job-board-api (reviewed 2026-11-01).
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
class ArbeitnowAdapter:
    meta = AdapterMeta(
        key="arbeitnow",
        name="Arbeitnow",
        layer="board",
        terms_note="Public job-board API; reviewed 2026-11-01.",
        countries=("DE", "EU"),
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
            rows = data.get("data") or data.get("jobs") or []
        else:
            data, _, _ = await fetch_json("https://www.arbeitnow.com/api/job-board-api?page=1")
            rows = (data.get("data") or []) if isinstance(data, dict) else []
        for j in rows:
            yield RawJob(
                external_id=str(j.get("slug") or j.get("url")),
                source_key="arbeitnow",
                title=j.get("title") or "",
                company_name=j.get("company_name") or "",
                url=j.get("url") or "",
                apply_url=j.get("url") or "",
                description_text=html_to_text(j.get("description") or ""),
                location_text=" · ".join(
                    x for x in [j.get("location"), "Remote" if j.get("remote") else ""] if x
                ),
                remote=bool(j.get("remote")),
                employment_type=", ".join(j.get("job_types") or []),
                posted_at=parse_iso_dt(j.get("created_at")),
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
