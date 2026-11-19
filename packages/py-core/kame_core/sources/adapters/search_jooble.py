"""Jooble keyword + location search API (Layer 4).

Terms: https://jooble.org/api/about and the official REST API help page. Checked 2026-11-13:
the free plan lists 100 requests/day per regional key, and a key is valid only on the domain that
issued it. Fixtures are allowed for tests. Live calls require the platform terms acknowledgement
(`SEARCH_TERMS_ACKNOWLEDGED=true`) plus the regional key. No logged-in scraping, no evasion.
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
class JoobleSearchAdapter:
    meta = AdapterMeta(
        key="search_jooble",
        name="Jooble search",
        layer="search",
        terms_note=(
            "Regional REST API. Free plan lists 100 requests/day per key; a key is valid only on "
            "its own country domain. Terms checked 2026-11-13."
        ),
        countries=(
            "PH",
            "AE",
            "SA",
            "QA",
            "KW",
            "SG",
            "MY",
            "GB",
            "US",
            "CA",
            "AU",
            "NZ",
            "DE",
            "FR",
            "NL",
            "IN",
        ),
        auth="api_key",
        rate_limit_per_minute=10,
        terms_verified=False,
        terms_url="https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation",
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_keys: Mapping[str, str] | None = None,
        fixture_dir: Path | None = None,
    ):
        self._api_key = api_key
        self._api_keys = {str(k).upper(): v for k, v in (api_keys or {}).items() if v}
        self._fixture_dir = fixture_dir

    def _key_for(self, country: str) -> str | None:
        if country and country in self._api_keys:
            return self._api_keys[country]
        # A bare jooble.org key belongs to the US domain. Never reuse it on another region.
        if not country or country == "US":
            return self._api_key
        return None

    def _host_for(self, country: str) -> str:
        """The domain that owns the key. US and unknown regions use the global jooble.org host."""
        if not country or country == "US" or country not in self._api_keys:
            return "https://jooble.org"
        return f"https://{country.lower()}.jooble.org"

    async def discover(self, params: Mapping[str, object]) -> AsyncIterator[RawJob]:
        query = SearchQuery.from_params(params)
        if self._fixture_dir:
            data = json.loads((self._fixture_dir / "jobs.json").read_text(encoding="utf-8"))
        else:
            country = query.country.upper() if query.country else ""
            key = self._key_for(country)
            if not key:
                return
            host = self._host_for(country)
            data, _, _ = await fetch_json(
                f"{host}/api/{key}",
                method="POST",
                json_body={
                    "keywords": query.keywords,
                    "location": query.location,
                    "page": str(max(1, query.page)),
                },
            )
        if not isinstance(data, dict):
            return
        for job in data.get("jobs") or []:
            if not isinstance(job, dict):
                continue
            description = str(job.get("description") or job.get("snippet") or "")
            text = html_to_text(description)
            salary = parse_salary_fragment(str(job.get("salary") or text))
            link = str(job.get("link") or "")
            yield RawJob(
                external_id=str(job.get("id") or link),
                source_key="search_jooble",
                title=str(job.get("title") or ""),
                company_name=str(job.get("company") or ""),
                url=link,
                apply_url=link,
                description_html=description,
                description_text=text,
                location_text=str(job.get("location") or ""),
                employment_type=str(job.get("type") or ""),
                posted_at=parse_iso_dt(job.get("updated")),
                salary_text=str(job.get("salary") or salary["salary_text"] or ""),
                salary_min=salary["salary_min"],  # type: ignore[arg-type]
                salary_max=salary["salary_max"],  # type: ignore[arg-type]
                salary_currency=salary["salary_currency"],  # type: ignore[arg-type]
                salary_period=salary["salary_period"],  # type: ignore[arg-type]
                raw={"provider": "jooble", "query": query.as_dict()},
            )

    async def fetch_detail(self, ref: Mapping[str, object]) -> RawJob | None:
        return None

    async def health(self) -> SourceHealth:
        return SourceHealth(ok=bool(self._api_key or self._fixture_dir), items=0)
