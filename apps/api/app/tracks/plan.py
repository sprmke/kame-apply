"""Pack-aware search plan (deterministic baseline for search_plan.v2)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.industries.detect import detect_industry
from app.industries.packs.general import GENERAL
from app.industries.registry import get_pack
from app.sources.search_service import plan_queries
from app.tracks.criteria import CriteriaV1, SalaryFilter, TitleSpec
from app.tracks.models import Track


class SearchPlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)
    industry: str | None = Field(default=None, max_length=48)


class SearchPlanQuery(BaseModel):
    keywords: str
    location: str = ""
    country: str = ""
    category: str | None = None


class SearchPlanOut(BaseModel):
    industry: str
    role_family: str | None
    confidence: float
    name: str
    criteria: dict[str, Any]
    titles: list[str]
    source_queries: list[SearchPlanQuery]
    reasons: list[str]
    source: str = "defaults"


def plan_search(body: SearchPlanIn) -> SearchPlanOut:
    detection = detect_industry(body.text)
    key = body.industry or detection.pack_key
    pack = get_pack(key) or GENERAL

    lowered = body.text.lower()
    titles: list[str] = []
    for family in pack.role_families:
        for title in family.titles:
            if title.lower() in lowered:
                titles.append(title)
    if not titles and pack.role_families:
        titles.append(pack.role_families[0].titles[0])
    if not titles:
        titles.append(body.text.strip()[:80])

    defaults = pack.criteria_defaults
    criteria = CriteriaV1(
        titles=[TitleSpec(title=title) for title in titles[:3]],
        employment_types=list(defaults.employment_types),
        work_modes=list(defaults.work_modes),
        shifts=list(defaults.shifts),
        posting_max_age_days=defaults.posting_max_age_days,
        salary=SalaryFilter(period=defaults.salary_period) if defaults.salary_period else None,
    )

    track = Track(name=f"{titles[0]} search", industry=key)
    queries = plan_queries(track, criteria, pack, limit=6)
    return SearchPlanOut(
        industry=key,
        role_family=detection.role_family,
        confidence=detection.confidence,
        name=f"{titles[0]} search",
        criteria=criteria.model_dump(mode="json"),
        titles=titles[:3],
        source_queries=[
            SearchPlanQuery(
                keywords=str(query.get("keywords") or ""),
                location=str(query.get("location") or ""),
                country=str(query.get("country") or ""),
                category=query.get("category"),
            )
            for query in queries
        ],
        reasons=detection.reasons,
    )
