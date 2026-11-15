"""Stage 1 hard filters: compiled criteria + knockouts → eligibility."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.industries.schema import IndustryPack
from app.jobs.normalize import normalize_title
from app.matching.rule_score import same_title_group, title_tokens
from app.tracks.criteria import CriteriaV1, criteria_from_dict

# A posting's coarse employment label → the CriteriaV1 types it satisfies.
_EMPLOYMENT = {
    "full_time": {"full_time"},
    "part_time": {"part_time"},
    "contract": {"contract", "freelance", "temporary"},
    "intern": {"internship"},
}


def _posted_before(value: Any, days: int) -> bool:
    if not value:
        return False
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return (datetime.now(UTC) - value).days > days


def hard_filter(
    job: dict[str, Any],
    structured: dict[str, Any] | CriteriaV1,
    *,
    knockout_hits: list[dict[str, Any]] | None = None,
    hidden_company_ids: set[str] | None = None,
    pack: IndustryPack | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return (eligibility, detail). eligibility: eligible | not_eligible | unknown."""
    c = structured if isinstance(structured, CriteriaV1) else criteria_from_dict(structured)
    detail: dict[str, Any] = {"failed": []}
    generic = set(pack.matching.generic_title_words) if pack else None

    if (
        hidden_company_ids
        and job.get("company_id")
        and str(job["company_id"]) in hidden_company_ids
    ):
        detail["failed"].append("hidden_company")
        return "not_eligible", detail

    if knockout_hits:
        detail["knockouts"] = knockout_hits
        detail["failed"].append("knockout")
        return "not_eligible", detail

    title_blob = f"{job.get('title', '')} {job.get('normalized_title', '')}".lower()
    norm = job.get("normalized_title") or normalize_title(job.get("title") or "")

    if c.titles:
        ok = False
        for t in c.titles:
            nt = normalize_title(t.title)
            if t.exclude:
                if nt and nt in norm:
                    detail["failed"].append(f"exclude_title:{t.title}")
                    return "not_eligible", detail
            elif nt in norm or t.title.lower() in title_blob:
                ok = True
            else:
                # Ignore generic words such as "lead" and "engineer"; a marketing lead is not a
                # support role just because both titles contain "lead".
                if pack is not None and same_title_group(pack, nt, norm):
                    ok = True
                elif title_tokens(norm, generic) & title_tokens(nt, generic):
                    ok = True
        if not ok and any(not t.exclude for t in c.titles):
            detail["failed"].append("title")
            return "not_eligible", detail

    if c.skills and c.skills.exclude:
        blob = f"{job.get('description_text', '')} {title_blob}".lower()
        for sk in c.skills.exclude:
            if sk.lower() in blob:
                detail["failed"].append(f"exclude_skill:{sk}")
                return "not_eligible", detail

    if c.work_modes and job.get("work_mode"):
        if job["work_mode"] not in c.work_modes and not (
            job["work_mode"] == "hybrid" and "remote" in c.work_modes
        ):
            detail["failed"].append("work_mode")
            return "not_eligible", detail

    if c.employment_types and job.get("employment_type"):
        allowed = _EMPLOYMENT.get(job["employment_type"], set())
        if allowed and not allowed & set(c.employment_types):
            detail["failed"].append("employment_type")
            return "not_eligible", detail

    if c.posting_max_age_days and _posted_before(job.get("posted_at"), c.posting_max_age_days):
        detail["failed"].append("posting_age")
        return "not_eligible", detail

    if c.salary and c.salary.hide_unspecified:
        sal = job.get("salary") or {}
        if sal.get("min") is None and sal.get("max") is None:
            detail["failed"].append("salary_unspecified")
            return "not_eligible", detail

    if c.companies and c.companies.exclude_agencies:
        name = (job.get("company_name") or "").lower()
        if any(x in name for x in ("staffing", "recruiting agency", "talent partner")):
            detail["failed"].append("agency")
            return "not_eligible", detail

    if pack is not None and c.facets:
        job_facets = job.get("facets") or {}
        for facet in pack.facets:
            if not facet.match.filter:
                continue
            wanted = c.facets.get(facet.key)
            wanted_values = set(wanted) if isinstance(wanted, list) else set()
            if not wanted_values:
                continue
            job_values = set(job_facets.get(facet.key) or [])
            if job_values and not (wanted_values & job_values):
                detail["failed"].append(f"facet:{facet.key}")
                return "not_eligible", detail

    return "eligible", detail
