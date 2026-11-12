"""Honest coverage and guided-alert links. No scraping, no automation of the boards."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import WorkspaceContext
from app.industries.packs.general import GENERAL
from app.industries.registry import get_pack
from app.sources.catalog import COUNTRY_COVERAGE
from app.sources.models import SourceCoverage
from app.sources.search_service import adapter_plan, plan_queries
from app.tracks.criteria import criteria_from_dict
from app.tracks.models import Track, TrackCriteria

LEVEL_ORDER = {"none": 0, "thin": 1, "partial": 2, "strong": 3}


def _level(value: str) -> str:
    return value if value in LEVEL_ORDER else "thin"


async def coverage_for(session: AsyncSession, *, industry: str, country: str) -> dict[str, Any]:
    country = country.upper()
    rows = list(
        (
            await session.execute(
                select(SourceCoverage).where(
                    SourceCoverage.industry == industry,
                    SourceCoverage.country.in_((country, "GLOBAL")),
                )
            )
        ).scalars()
    )
    if not rows and industry == "technology":
        for item in COUNTRY_COVERAGE:
            if item["country"] not in (country, "GLOBAL", "REMOTE"):
                continue
            rows.append(
                SourceCoverage(
                    source_key=item["source_key"],
                    country=item["country"],
                    industry="technology",
                    coverage=item["coverage"],
                    note=item["note"],
                )
            )
    if not rows:
        return {
            "industry": industry,
            "country": country,
            "level": "none",
            "sources": [],
            "note": "No source covers this field in this country yet.",
        }
    best = max((_level(row.coverage) for row in rows), key=lambda level: LEVEL_ORDER[level])
    return {
        "industry": industry,
        "country": country,
        "level": best,
        "sources": [
            {
                "source_key": row.source_key,
                "coverage": _level(row.coverage),
                "note": row.note,
            }
            for row in rows
        ],
        "note": next((row.note for row in rows if row.coverage == best), ""),
    }


async def where_for_track(ctx: WorkspaceContext, track_id, settings: Settings) -> dict[str, Any]:
    track = await ctx.session.get(Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        from app.core.errors import AppError

        raise AppError("not_found", "Track not found", 404)
    crit = (
        await ctx.session.execute(select(TrackCriteria).where(TrackCriteria.track_id == track_id))
    ).scalar_one_or_none()
    criteria = criteria_from_dict(crit.structured if crit else {})
    pack = get_pack(track.industry) or GENERAL
    queries = plan_queries(track, criteria, pack, limit=settings.search_queries_per_track)
    return {
        "industry": track.industry,
        "queries": [
            {
                "keywords": query["keywords"],
                "location": query.get("location") or "",
                "country": query.get("country") or "",
                "category": query.get("category"),
            }
            for query in queries
        ],
        "adapters": adapter_plan(pack, settings),
        "employer_tags": list(pack.sources.employer_tags),
        "alerts": list(pack.sources.alert_sources),
    }


def _indeed_host(country: str) -> str:
    hosts = {
        "PH": "https://ph.indeed.com/jobs",
        "AE": "https://ae.indeed.com/jobs",
        "GB": "https://uk.indeed.com/jobs",
        "AU": "https://au.indeed.com/jobs",
        "CA": "https://ca.indeed.com/jobs",
    }
    return hosts.get(country, "https://www.indeed.com/jobs")


def _jobstreet_url(country: str) -> str | None:
    hosts = {
        "PH": "https://www.jobstreet.com.ph/jobs",
        "MY": "https://www.jobstreet.com.my/jobs",
        "SG": "https://www.jobstreet.com.sg/jobs",
        "ID": "https://www.jobstreet.co.id/jobs",
    }
    return hosts.get(country)


def alerts_guide(
    *, industry: str, country: str, keywords: str, location: str
) -> list[dict[str, str]]:
    """Prefilled public search URLs the person can turn into an email alert themselves."""
    pack = get_pack(industry) or GENERAL
    country = country.upper()
    q = keywords.strip()
    loc = location.strip()
    out: list[dict[str, str]] = []
    for provider in pack.sources.alert_sources:
        if provider == "indeed":
            url = f"{_indeed_host(country)}?{urlencode({'q': q, 'l': loc, 'fromage': '7'})}"
            out.append(
                {
                    "provider": "indeed",
                    "label": "Indeed",
                    "url": url,
                    "note": "Create or open a search, then choose 'Create alert'. Forward the email to your Kame address.",
                }
            )
        elif provider == "jobstreet":
            base = _jobstreet_url(country)
            if base:
                url = f"{base}?{urlencode({'keywords': q, 'where': loc})}"
                out.append(
                    {
                        "provider": "jobstreet",
                        "label": "JobStreet",
                        "url": url,
                        "note": "Save the search and turn on email alerts. Forward one alert to your Kame address.",
                    }
                )
        elif provider == "linkedin":
            url = f"https://www.linkedin.com/jobs/search/?{urlencode({'keywords': q, 'location': loc})}"
            out.append(
                {
                    "provider": "linkedin",
                    "label": "LinkedIn Jobs",
                    "url": url,
                    "note": "Create a job alert in your own account. Kame never signs in to LinkedIn for you.",
                }
            )
    if industry == "hospitality":
        url = f"https://culinaryagents.com/jobs?{urlencode({'search': q})}"
        out.append(
            {
                "provider": "culinary_agents",
                "label": "Culinary Agents",
                "url": url,
                "note": "Set an alert in your own account, then forward it to your Kame address.",
            }
        )
    return out


async def source_advice(session: AsyncSession, *, industry: str, country: str) -> dict[str, Any]:
    from app.industries.packs.general import GENERAL
    from app.industries.registry import get_pack

    pack = get_pack(industry) or GENERAL
    coverage = await coverage_for(session, industry=industry, country=country)
    suggestions: list[dict[str, Any]] = []
    for provider in pack.sources.alert_sources:
        suggestions.append(
            {
                "kind": "alert",
                "provider": provider,
                "text": f"Create a {provider} alert for this search and forward it to Kame.",
            }
        )
    for tag in pack.sources.employer_tags[:3]:
        suggestions.append(
            {
                "kind": "careers",
                "text": f"Add a {tag} employer careers page so we can read its postings.",
            }
        )
    return {
        "industry": industry,
        "country": country.upper(),
        "coverage": coverage["level"],
        "employer_tags": list(pack.sources.employer_tags),
        "alert_sources": list(pack.sources.alert_sources),
        "suggestions": suggestions,
    }
