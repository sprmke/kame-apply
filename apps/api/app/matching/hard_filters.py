"""Stage 1 hard filters: compiled criteria + knockouts → eligibility."""

from __future__ import annotations

from typing import Any

from app.jobs.normalize import normalize_title
from app.matching.rule_score import title_tokens
from app.tracks.criteria import CriteriaV1, criteria_from_dict


def hard_filter(
    job: dict[str, Any],
    structured: dict[str, Any] | CriteriaV1,
    *,
    knockout_hits: list[dict[str, Any]] | None = None,
    hidden_company_ids: set[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return (eligibility, detail). eligibility: eligible | not_eligible | unknown."""
    c = structured if isinstance(structured, CriteriaV1) else criteria_from_dict(structured)
    detail: dict[str, Any] = {"failed": []}

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
                if title_tokens(norm) & title_tokens(nt):
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

    return "eligible", detail
