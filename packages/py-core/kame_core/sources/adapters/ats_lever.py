"""Lever postings API (US + EU hosts).

Terms: https://github.com/lever/postings-api (public JSON, reviewed 2026-11-01).
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
class LeverAdapter:
    meta = AdapterMeta(
        key="lever",
        name="Lever",
        layer="ats",
        terms_note="Public postings API; reviewed 2026-11-01.",
        rate_limit_per_minute=20,
    )

    def __init__(self, *, fixture_dir: Path | None = None, eu: bool = False):
        self._fixture_dir = fixture_dir
        self._eu = eu

    async def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        slug = require_slug(params)
        eu = bool(params.get("eu", self._eu))
        if self._fixture_dir:
            import json

            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            host = "api.eu.lever.co" if eu else "api.lever.co"
            data, _, _ = await fetch_json(f"https://{host}/v0/postings/{slug}?mode=json")
        rows = data if isinstance(data, list) else []
        for j in rows:
            lists = "\n".join(
                f"{(lst.get('text') or '')}\n{html_to_text(lst.get('content') or '')}"
                for lst in (j.get("lists") or [])
            )
            text = "\n".join(
                filter(
                    None,
                    [j.get("descriptionPlain"), lists, j.get("additionalPlain")],
                )
            )
            locs = j.get("categories", {}).get("allLocations") or [
                j.get("categories", {}).get("location")
            ]
            loc = " / ".join(x for x in locs if x)
            wt = j.get("workplaceType")
            remote = True if wt == "remote" else False if wt == "onsite" else None
            sal = parse_salary_fragment(text)
            yield RawJob(
                external_id=str(j.get("id")),
                source_key="lever",
                title=j.get("text") or "",
                company_name=name_from_slug(slug),
                url=j.get("hostedUrl") or "",
                apply_url=j.get("applyUrl") or j.get("hostedUrl") or "",
                description_text=text,
                location_text=loc,
                remote=remote,
                employment_type=(j.get("categories") or {}).get("commitment") or "",
                ats="lever",
                board_slug=slug,
                posted_at=parse_iso_dt(j.get("createdAt")),
                salary_text=str(sal["salary_text"] or ""),
                salary_min=sal["salary_min"],  # type: ignore[arg-type]
                salary_max=sal["salary_max"],  # type: ignore[arg-type]
                salary_currency=sal["salary_currency"],  # type: ignore[arg-type]
                salary_period=sal["salary_period"],  # type: ignore[arg-type]
            )

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
