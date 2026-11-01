"""Greenhouse Job Board API.

Terms: https://developers.greenhouse.io/job-board.html (public board API, 2026-11-01).
Attribution: link to absolute_url; do not republish JD off-platform.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

from kame_core.sources.adapters._common import health_ping, require_slug
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
class GreenhouseAdapter:
    meta = AdapterMeta(
        key="greenhouse",
        name="Greenhouse",
        layer="ats",
        terms_note="Public Job Board API; reviewed 2026-11-01.",
        rate_limit_per_minute=20,
    )

    def __init__(self, *, fixture_dir: Path | None = None):
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        slug = require_slug(params)
        if self._fixture_dir:
            data = json_load(self._fixture_dir / "jobs.json")
        else:
            data, _, _ = await fetch_json(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
            )
        if not isinstance(data, dict):
            data = {}
        for j in data.get("jobs") or []:
            html = j.get("content") or ""
            text = html_to_text(html)
            sal = parse_salary_fragment(text)
            loc = (j.get("location") or {}).get("name") or ""
            yield RawJob(
                external_id=str(j["id"]),
                source_key="greenhouse",
                title=j.get("title") or "",
                company_name=j.get("company_name") or name_from_slug(slug),
                url=j.get("absolute_url") or "",
                apply_url=j.get("absolute_url") or "",
                description_html=html,
                description_text=text,
                location_text=loc,
                remote=bool(loc and "remote" in loc.lower()) or None,
                ats="greenhouse",
                board_slug=slug,
                posted_at=parse_iso_dt(j.get("first_published") or j.get("updated_at")),
                salary_text=str(sal["salary_text"] or ""),
                salary_min=sal["salary_min"],  # type: ignore[arg-type]
                salary_max=sal["salary_max"],  # type: ignore[arg-type]
                salary_currency=sal["salary_currency"],  # type: ignore[arg-type]
                salary_period=sal["salary_period"],  # type: ignore[arg-type]
                raw={"id": j.get("id")},
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        if self._fixture_dir:
            return SourceHealth(ok=True, latency_ms=1.0, items=1)
        return await health_ping("https://boards-api.greenhouse.io/v1/boards/example/jobs")


def json_load(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
