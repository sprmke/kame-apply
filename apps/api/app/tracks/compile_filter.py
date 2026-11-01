"""Compile CriteriaV1 into versioned predicate descriptors for Phase 6 scoring.

Descriptors are JSON-safe; they never embed raw SQL. Phase 6 turns them into queries.
"""

from __future__ import annotations

from typing import Any

from app.tracks.criteria import CriteriaV1
from app.tracks.currency import normalize_salary

COMPILED_VERSION = 1


def compile_filter(criteria: CriteriaV1) -> dict[str, Any]:
    c = normalize_salary(criteria)
    predicates: list[dict[str, Any]] = []
    weights: dict[str, float] = {
        "title": 1.0,
        "occupation": 0.9,
        "skill_must": 1.2,
        "skill_nice": 0.4,
        "seniority": 0.5,
        "location": 0.7,
        "salary": 0.6,
        "company": 0.5,
    }

    include_titles = [t for t in c.titles if not t.exclude]
    exclude_titles = [t.title for t in c.titles if t.exclude]
    if include_titles:
        predicates.append(
            {
                "op": "title_any",
                "values": [
                    {"title": t.title, "synonyms": list(t.synonyms)} for t in include_titles
                ],
            }
        )
    if exclude_titles:
        predicates.append({"op": "title_none", "values": exclude_titles})

    if c.occupations:
        predicates.append(
            {
                "op": "occupation_any",
                "values": [{"scheme": o.scheme, "code": o.code} for o in c.occupations],
            }
        )

    if c.skills.must:
        predicates.append({"op": "skills_all", "values": list(c.skills.must)})
    if c.skills.nice:
        predicates.append({"op": "skills_boost", "values": list(c.skills.nice)})
    if c.skills.exclude:
        predicates.append({"op": "skills_none", "values": list(c.skills.exclude)})

    if c.seniority:
        predicates.append({"op": "seniority_any", "values": list(c.seniority)})
    if c.employment_types:
        predicates.append({"op": "employment_type_any", "values": list(c.employment_types)})
    if c.work_modes:
        predicates.append({"op": "work_mode_any", "values": list(c.work_modes)})

    rem = c.remote_eligibility
    if rem.anywhere or rem.regions or rem.countries or rem.timezone_overlap_hours is not None:
        predicates.append(
            {
                "op": "remote_eligibility",
                "anywhere": rem.anywhere,
                "regions": list(rem.regions),
                "countries": list(rem.countries),
                "timezone_overlap_hours": rem.timezone_overlap_hours,
                "base_tz": rem.base_tz,
            }
        )

    if c.locations:
        predicates.append(
            {
                "op": "location_any",
                "values": [
                    {
                        "place": loc.place,
                        "radius_km": loc.radius_km,
                        "lat": loc.lat,
                        "lon": loc.lon,
                        "country": loc.country,
                    }
                    for loc in c.locations
                ],
            }
        )

    if c.visa_sponsorship is not None:
        predicates.append({"op": "visa_sponsorship", "value": c.visa_sponsorship})
    if c.relocation is not None:
        predicates.append({"op": "relocation", "value": c.relocation})

    if c.salary:
        s = c.salary
        predicates.append(
            {
                "op": "salary",
                "min": s.min,
                "max": s.max,
                "currency": s.currency,
                "period": s.period,
                "hide_unspecified": s.hide_unspecified,
                "min_monthly_usd": s.min_monthly_usd,
                "max_monthly_usd": s.max_monthly_usd,
                "rate_missing": s.rate_missing,
            }
        )

    co = c.companies
    if any([co.include, co.exclude, co.sizes, co.industries, co.stages, co.exclude_agencies]):
        predicates.append(
            {
                "op": "company",
                "include": list(co.include),
                "exclude": list(co.exclude),
                "sizes": list(co.sizes),
                "industries": list(co.industries),
                "stages": list(co.stages),
                "exclude_agencies": co.exclude_agencies,
            }
        )

    if c.posting_max_age_days is not None:
        predicates.append({"op": "posting_max_age_days", "value": c.posting_max_age_days})
    if c.languages:
        predicates.append({"op": "languages_any", "values": list(c.languages)})
    if c.education:
        predicates.append({"op": "education", "value": c.education})
    if c.clearance:
        predicates.append({"op": "clearance", "value": c.clearance})
    if c.keywords.include_expr:
        predicates.append({"op": "keyword_include", "expr": c.keywords.include_expr})
    if c.keywords.exclude_expr:
        predicates.append({"op": "keyword_exclude", "expr": c.keywords.exclude_expr})
    if c.min_match_score is not None:
        predicates.append({"op": "min_match_score", "value": c.min_match_score})
    if c.caps.per_day is not None or c.caps.per_company is not None:
        predicates.append(
            {"op": "caps", "per_day": c.caps.per_day, "per_company": c.caps.per_company}
        )

    return {
        "version": COMPILED_VERSION,
        "predicates": predicates,
        "weights": weights,
    }
