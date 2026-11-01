"""Himalayas search API.

Terms: public search JSON; link back; personal use (reviewed 2026-11-01).
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
class HimalayasAdapter:
    meta = AdapterMeta(
        key="himalayas",
        name="Himalayas",
        layer="board",
        terms_note="Public search API; reviewed 2026-11-01.",
        countries=("REMOTE",),
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            q = params.get("q") or "software engineer"
            data, _, _ = await fetch_json(
                f"https://himalayas.app/jobs/api/search?q={q}&sort=recent&page=1"
            )
        if not isinstance(data, dict):
            data = {}
        for j in data.get("jobs") or []:
            text = html_to_text(j.get("description") or "")
            restrictions = j.get("locationRestrictions") or []
            yield RawJob(
                external_id=str(j.get("guid") or j.get("id")),
                source_key="himalayas",
                title=j.get("title") or "",
                company_name=j.get("companyName") or "",
                url=j.get("applicationLink") or j.get("guid") or "",
                apply_url=j.get("applicationLink") or j.get("guid") or "",
                description_text=text,
                location_text=(
                    f"Remote ({len(restrictions)} countries)"
                    if restrictions
                    else "Remote (worldwide)"
                ),
                remote=True,
                allowed_countries=list(restrictions),
                employment_type=j.get("employmentType") or "",
                posted_at=parse_iso_dt(j.get("pubDate")),
                salary_min=float(j["minSalary"]) if j.get("minSalary") else None,
                salary_max=float(j["maxSalary"]) if j.get("maxSalary") else None,
                salary_currency=j.get("currency"),
                salary_period=j.get("salaryPeriod"),
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
