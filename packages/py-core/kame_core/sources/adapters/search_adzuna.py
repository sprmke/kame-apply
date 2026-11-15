"""Adzuna keyword + location search API (Layer 4).

Terms: https://developer.adzuna.com/terms. Free-tier quota, attribution, and link-back rules must
be confirmed before live use; `terms_verified` stays false until then. Fixtures are allowed for
tests. Live calls require the platform terms acknowledgement plus ADZUNA_APP_ID / ADZUNA_APP_KEY.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from pathlib import Path

from kame_core.sources.base import AdapterMeta, RawJob, SourceHealth
from kame_core.sources.http import fetch_json
from kame_core.sources.registry import register_adapter
from kame_core.sources.search import SearchQuery
from kame_core.sources.textutil import html_to_text, parse_iso_dt, parse_salary_fragment


@register_adapter
class AdzunaSearchAdapter:
    meta = AdapterMeta(
        key="search_adzuna",
        name="Adzuna search",
        layer="search",
        terms_note=(
            "Keyword and location search API with category tags. Free-tier quota, attribution, "
            "and display rules must be confirmed before live use (2026-11-13)."
        ),
        countries=(
            "GB",
            "US",
            "AT",
            "AU",
            "BE",
            "BR",
            "CA",
            "CH",
            "DE",
            "ES",
            "FR",
            "IN",
            "IT",
            "MX",
            "NL",
            "NZ",
            "PL",
            "SG",
            "ZA",
        ),
        auth="api_key",
        rate_limit_per_minute=10,
        terms_verified=False,
        terms_url="https://developer.adzuna.com/terms",
    )

    def __init__(
        self,
        *,
        app_id: str | None = None,
        app_key: str | None = None,
        fixture_dir: Path | None = None,
    ):
        self._app_id = app_id
        self._app_key = app_key
        self._fixture_dir = fixture_dir

    async def discover(self, params: Mapping[str, object]) -> AsyncIterator[RawJob]:
        query = SearchQuery.from_params(params)
        if self._fixture_dir:
            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        elif self._app_id and self._app_key and query.country:
            country = query.country.lower()
            page = max(1, query.page)
            url = (
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
                f"?app_id={self._app_id}&app_key={self._app_key}"
                "&results_per_page=50&content-type=application/json"
            )
            if query.keywords:
                url += f"&what={query.keywords}"
            if query.location:
                url += f"&where={query.location}"
            if query.category:
                url += f"&category={query.category}"
            if query.posted_within_days:
                url += f"&max_days_old={query.posted_within_days}"
            data, _, _ = await fetch_json(url)
        else:
            return
        if not isinstance(data, dict):
            return
        for job in data.get("results") or []:
            if not isinstance(job, dict):
                continue
            description = str(job.get("description") or "")
            text = html_to_text(description)
            salary = parse_salary_fragment(text)
            location = job.get("location") or {}
            company = job.get("company") or {}
            link = str(job.get("redirect_url") or "")
            yield RawJob(
                external_id=str(job.get("id") or link),
                source_key="search_adzuna",
                title=str(job.get("title") or ""),
                company_name=str(company.get("display_name") or ""),
                url=link,
                apply_url=link,
                description_html=description,
                description_text=text,
                location_text=str(location.get("display_name") or ""),
                employment_type=str(job.get("contract_time") or job.get("contract_type") or ""),
                posted_at=parse_iso_dt(job.get("created")),
                salary_text=str(salary["salary_text"] or ""),
                salary_min=job.get("salary_min") or salary["salary_min"],  # type: ignore[arg-type]
                salary_max=job.get("salary_max") or salary["salary_max"],  # type: ignore[arg-type]
                salary_currency=salary["salary_currency"],  # type: ignore[arg-type]
                salary_period=salary["salary_period"],  # type: ignore[arg-type]
                allowed_countries=[query.country] if query.country else [],
                raw={"provider": "adzuna", "query": query.as_dict()},
            )

    async def fetch_detail(self, ref: Mapping[str, object]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=bool((self._app_id and self._app_key) or self._fixture_dir), items=0)
