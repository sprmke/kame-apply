"""Remote OK public API.

Terms: https://remoteok.com/api - attribution + link back; no republish (2026-11-01).
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
class RemoteOkAdapter:
    meta = AdapterMeta(
        key="remoteok",
        name="Remote OK",
        layer="board",
        terms_note="Public API; attribution required. Reviewed 2026-11-01.",
        countries=("REMOTE",),
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            data, _, _ = await fetch_json("https://remoteok.com/api")
        rows = data if isinstance(data, list) else []
        for j in rows:
            if not j or not j.get("id") or not j.get("position"):
                continue
            text = html_to_text(j.get("description") or "")
            yield RawJob(
                external_id=str(j.get("id")),
                source_key="remoteok",
                title=j.get("position") or "",
                company_name=j.get("company") or "",
                url=j.get("url") or "",
                apply_url=j.get("apply_url") or j.get("url") or "",
                description_text=text,
                location_text=j.get("location") or "Remote",
                remote=True,
                posted_at=parse_iso_dt(j.get("date")),
                salary_min=float(j["salary_min"]) if j.get("salary_min") else None,
                salary_max=float(j["salary_max"]) if j.get("salary_max") else None,
                salary_currency="USD" if j.get("salary_min") else None,
                salary_period="year" if j.get("salary_min") else None,
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
