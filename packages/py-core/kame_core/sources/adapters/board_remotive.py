"""Remotive remote jobs API.

Terms: https://remotive.com/api-documentation - personal use, link back, no republish (2026-11-01).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

from kame_core.sources.base import AdapterMeta, RawJob, SourceHealth
from kame_core.sources.http import fetch_json
from kame_core.sources.registry import register_adapter
from kame_core.sources.textutil import html_to_text, parse_iso_dt, parse_salary_fragment


@register_adapter
class RemotiveAdapter:
    meta = AdapterMeta(
        key="remotive",
        name="Remotive",
        layer="board",
        terms_note="Public API; attribution required; no republish. Reviewed 2026-11-01.",
        countries=("REMOTE",),
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            cat = params.get("category") or "software-dev"
            data, _, _ = await fetch_json(
                f"https://remotive.com/api/remote-jobs?category={cat}&limit=100"
            )
        if not isinstance(data, dict):
            data = {}
        for j in data.get("jobs") or []:
            text = html_to_text(j.get("description") or "")
            sal = parse_salary_fragment(j.get("salary") or text)
            yield RawJob(
                external_id=str(j.get("id")),
                source_key="remotive",
                title=j.get("title") or "",
                company_name=j.get("company_name") or "",
                url=j.get("url") or "",
                apply_url=j.get("url") or "",
                description_text=text,
                location_text=j.get("candidate_required_location") or "Remote",
                remote=True,
                employment_type=j.get("job_type") or "",
                posted_at=parse_iso_dt(j.get("publication_date")),
                salary_text=str(j.get("salary") or sal["salary_text"] or ""),
                salary_min=sal["salary_min"],  # type: ignore[arg-type]
                salary_max=sal["salary_max"],  # type: ignore[arg-type]
                salary_currency=sal["salary_currency"],  # type: ignore[arg-type]
                salary_period=sal["salary_period"],  # type: ignore[arg-type]
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
