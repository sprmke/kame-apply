"""Ashby posting API.

Terms: https://developers.ashbyhq.com/docs/public-job-posting-api (reviewed 2026-11-01).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

from kame_core.sources.adapters._common import require_slug
from kame_core.sources.base import AdapterMeta, RawJob, SourceHealth
from kame_core.sources.http import fetch_json
from kame_core.sources.registry import register_adapter
from kame_core.sources.textutil import (
    html_to_text,
    name_from_slug,
    parse_iso_dt,
    parse_salary_fragment,
)


@register_adapter
class AshbyAdapter:
    meta = AdapterMeta(
        key="ashby",
        name="Ashby",
        layer="ats",
        terms_note="Public job posting API; reviewed 2026-11-01.",
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
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
            )
        if not isinstance(data, dict):
            data = {}
        for j in data.get("jobs") or []:
            if j.get("isListed") is False:
                continue
            text = j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml") or "")
            locs = [
                j.get("location"),
                *[(s or {}).get("location") for s in (j.get("secondaryLocations") or [])],
            ]
            loc = " / ".join(x for x in locs if x)
            remote = (
                True
                if j.get("isRemote") is True or j.get("workplaceType") == "Remote"
                else False
                if j.get("workplaceType") == "OnSite"
                else None
            )
            comp = (
                (j.get("compensation") or {}).get("compensationTierSummary")
                or (j.get("compensation") or {}).get("scrapeableCompensationSalarySummary")
                or ""
            )
            sal = parse_salary_fragment(comp or text)
            yield RawJob(
                external_id=str(j.get("id")),
                source_key="ashby",
                title=j.get("title") or "",
                company_name=name_from_slug(slug),
                url=j.get("jobUrl") or "",
                apply_url=j.get("applyUrl") or j.get("jobUrl") or "",
                description_text=text,
                location_text=loc,
                remote=remote,
                employment_type=j.get("employmentType") or "",
                ats="ashby",
                board_slug=slug,
                posted_at=parse_iso_dt(j.get("publishedAt")),
                salary_text=str(comp or sal["salary_text"] or ""),
                salary_min=sal["salary_min"],  # type: ignore[arg-type]
                salary_max=sal["salary_max"],  # type: ignore[arg-type]
                salary_currency=sal["salary_currency"],  # type: ignore[arg-type]
                salary_period=sal["salary_period"],  # type: ignore[arg-type]
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
