"""Zero-result relaxation suggestions via cheap counts."""

from __future__ import annotations

from typing import Any

from app.tracks.criteria import CriteriaV1, criteria_from_dict


def suggest_relaxations(
    *,
    criteria: dict[str, Any] | CriteriaV1,
    jobs: list[dict[str, Any]],
    hard_filter_fn,
) -> list[dict[str, Any]]:
    """For each active filter, count how many jobs become eligible if relaxed."""
    c = criteria if isinstance(criteria, CriteriaV1) else criteria_from_dict(criteria)
    base_eligible = sum(1 for j in jobs if hard_filter_fn(j, c)[0] == "eligible")
    suggestions: list[dict[str, Any]] = []

    variants: list[tuple[str, CriteriaV1]] = []
    if c.salary and (c.salary.min is not None or c.salary.hide_unspecified):
        relaxed = c.model_copy(deep=True)
        relaxed.salary = None
        variants.append(("Remove salary floor", relaxed))
    if c.skills and c.skills.must:
        relaxed = c.model_copy(deep=True)
        relaxed.skills = relaxed.skills.model_copy(update={"must": []})
        variants.append(("Drop must-skills", relaxed))
    if c.work_modes:
        relaxed = c.model_copy(deep=True)
        relaxed.work_modes = []
        variants.append(("Any work mode", relaxed))
    if c.seniority:
        relaxed = c.model_copy(deep=True)
        relaxed.seniority = []
        variants.append(("Any seniority", relaxed))
    if c.remote_eligibility.countries or c.remote_eligibility.regions:
        relaxed = c.model_copy(deep=True)
        relaxed.remote_eligibility = relaxed.remote_eligibility.model_copy(
            update={"countries": [], "regions": [], "anywhere": True}
        )
        variants.append(("Widen location", relaxed))
    if c.companies and c.companies.exclude_agencies:
        relaxed = c.model_copy(deep=True)
        relaxed.companies = relaxed.companies.model_copy(update={"exclude_agencies": False})
        variants.append(("Allow agencies", relaxed))

    for label, variant in variants:
        n = sum(1 for j in jobs if hard_filter_fn(j, variant)[0] == "eligible")
        gained = n - base_eligible
        if gained > 0:
            suggestions.append({"label": label, "gained": gained, "total": n})

    suggestions.sort(key=lambda x: x["gained"], reverse=True)
    return suggestions
