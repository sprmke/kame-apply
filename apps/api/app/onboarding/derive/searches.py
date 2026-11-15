"""Search proposals: one to three variants, always wide enough to find work.

Titles are a hard filter in matching, so every proposal carries market synonyms and never an
excluded title. Must-have skills are always a subset of the person's skills; languages, salary,
visa, and education are not set from a resume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.onboarding import schemas as s
from app.onboarding.derive import automation
from app.onboarding.derive import seniority as seniority_rules
from app.onboarding.derive import skills as skill_rules
from app.onboarding.derive import titles as title_rules
from app.onboarding.derive.locale import locale_for, timezone_for
from app.tracks.criteria import (
    CriteriaV1,
    LocationFilter,
    RemoteEligibility,
    SkillSets,
    TitleSpec,
)
from app.tracks.plan import baseline_plan, plan_from_model
from app.tracks.summary import summarize

MAX_TITLES = 5


@dataclass
class SearchInput:
    experiences: list[dict[str, Any]] = field(default_factory=list)
    headline: str = ""
    location: str = ""
    country: str = ""
    profile_skills: list[str] = field(default_factory=list)
    role_text: str = ""
    device_timezone: str = "UTC"
    today: date | None = None


def _timezone(inp: SearchInput) -> str:
    return timezone_for(inp.country, inp.device_timezone) or inp.device_timezone or "UTC"


def _variant_sentence(variant: str, inp: SearchInput, latest_title: str) -> str:
    if variant == "you_said":
        return inp.role_text.strip()
    if variant == "step_up":
        base = title_rules.step_up_title(latest_title)
        return f"{base} in {inp.location}" if inp.location else base
    return f"{latest_title} in {inp.location}" if inp.location else latest_title


def _name_for(title: str, inp: SearchInput, *, remote: bool) -> str:
    place = (inp.location or "").split(",")[0].strip()
    if place and remote:
        return f"{title}, {place} or remote"[:200]
    if place:
        return f"{title}, {place}"[:200]
    return f"{title}, remote"[:200] if remote else title[:200]


def _merge_titles(
    *,
    primary: list[str],
    synonyms: list[str],
    base: CriteriaV1,
) -> list[TitleSpec]:
    out: list[TitleSpec] = []
    seen: set[str] = set()
    if primary:
        first = primary[0]
        seen.add(first.casefold())
        out.append(TitleSpec(title=first, synonyms=synonyms[:5]))
        for title in primary[1:]:
            if title.casefold() in seen:
                continue
            seen.add(title.casefold())
            out.append(TitleSpec(title=title))
    for spec in base.titles:
        if spec.exclude:
            continue
        if spec.title.casefold() in seen:
            continue
        seen.add(spec.title.casefold())
        out.append(TitleSpec(title=spec.title, synonyms=spec.synonyms[:3]))
        if len(out) >= MAX_TITLES:
            break
    return out[:MAX_TITLES]


def _history_employment(experiences: list[dict[str, Any]], fallback: list[str]) -> list[str]:
    if fallback:
        return fallback
    recent = [str(exp.get("employment_type") or "full_time") for exp in experiences[:3]]
    flexible = {
        "contract",
        "freelance",
        "part_time",
        "temporary",
    }
    if sum(1 for kind in recent if kind in flexible) >= 2:
        return ["contract", "freelance", "part_time", "full_time"]
    return ["full_time"]


def build_one(
    *,
    inp: SearchInput,
    variant: str,
    sentence: str,
    latest_title: str,
    titles: list[str],
    synonyms: list[str],
) -> s.SearchProposal:
    base = baseline_plan(sentence)
    levels = seniority_rules.suggest_levels(
        latest_title=latest_title,
        experiences=inp.experiences,
        today=inp.today,
    )
    locale = locale_for(inp.country)
    role_skills = [*base.skills.must, *base.skills.nice]
    must = skill_rules.must_have(
        profile_skills=inp.profile_skills,
        role_skills=role_skills,
        experiences=inp.experiences,
    )
    nice = skill_rules.nice_to_have(
        profile_skills=inp.profile_skills,
        role_skills=role_skills,
        must=must,
    )
    primary = titles or [latest_title or base.titles[0].title]
    criteria = CriteriaV1(
        titles=_merge_titles(primary=primary, synonyms=synonyms, base=base),
        skills=SkillSets(must=must, nice=nice),
        seniority=levels,  # type: ignore[arg-type]
        employment_types=_history_employment(inp.experiences, list(base.employment_types)),  # type: ignore[arg-type]
        work_modes=list(base.work_modes),
        remote_eligibility=RemoteEligibility(
            anywhere=base.remote_eligibility.anywhere,
            regions=list(base.remote_eligibility.regions),
            countries=[inp.country.upper()] if inp.country else [],
            base_tz=_timezone(inp),
        ),
        locations=(
            [
                LocationFilter(
                    place=inp.location.strip()[:200],
                    radius_km=locale.radius_km,
                    country=inp.country.upper() or None,
                )
            ]
            if inp.location.strip()
            else []
        ),
        visa_sponsorship=base.visa_sponsorship,
        relocation=base.relocation,
        salary=None,
        companies=base.companies,
        posting_max_age_days=21,
        languages=[],
        education=None,
        clearance=None,
        min_match_score=None,
    )
    return s.SearchProposal(
        variant=variant,  # type: ignore[arg-type]
        name=_name_for(primary[0], inp, remote="remote" in criteria.work_modes),
        nl_text=sentence[:2000],
        criteria=criteria,
        summary=summarize(criteria),
        autonomy=automation.AUTONOMY,  # type: ignore[arg-type]
        schedule=s.ScheduleDefaults(**automation.schedule_defaults(timezone=_timezone(inp))),
        adjacent_titles=[],
    )


def _family(title: str) -> set[str]:
    from app.onboarding.derive.seniority import _family_tokens

    return _family_tokens(title)


def _same_role(role_text: str, latest_title: str) -> bool:
    from app.tracks.plan import _extract_title

    if not role_text.strip():
        return False
    wanted = _family(_extract_title(role_text))
    current = _family(latest_title)
    return bool(wanted) and bool(current) and wanted == current


def build_all(inp: SearchInput) -> list[s.SearchProposal]:
    """Up to three variants. The role sentence wins when it points somewhere new."""
    experiences = inp.experiences
    latest_title = ""
    if experiences:
        latest_title = title_rules.clean_title(str(experiences[0].get("title") or ""))
    if not latest_title:
        latest_title = title_rules.headline_title(inp.headline)
    titles, synonyms = title_rules.role_titles(experiences=experiences, headline=inp.headline)

    proposals: list[s.SearchProposal] = []
    if inp.role_text.strip():
        sentence = _variant_sentence("you_said", inp, latest_title or "role")
        proposals.append(
            build_one(
                inp=inp,
                variant="you_said",
                sentence=sentence,
                latest_title=latest_title
                or title_rules.headline_title(inp.headline)
                or "Professional",
                titles=titles,
                synonyms=synonyms,
            )
        )
    if latest_title and not _same_role(inp.role_text, latest_title):
        proposals.append(
            build_one(
                inp=inp,
                variant="same_role",
                sentence=_variant_sentence("same_role", inp, latest_title),
                latest_title=latest_title,
                titles=titles,
                synonyms=synonyms,
            )
        )
    if latest_title and seniority_rules.step_up_allowed(
        latest_title=latest_title, experiences=experiences, today=inp.today
    ):
        proposals.append(
            build_one(
                inp=inp,
                variant="step_up",
                sentence=_variant_sentence("step_up", inp, latest_title),
                latest_title=title_rules.step_up_title(latest_title),
                titles=[title_rules.step_up_title(latest_title)],
                synonyms=[],
            )
        )
    for proposal in proposals:
        if proposal.variant == "step_up":
            proposal.default_on = False
    return proposals[:3]


def apply_model(
    proposals: list[s.SearchProposal], outputs: list[dict[str, Any]], inp: SearchInput
) -> list[s.SearchProposal]:
    """Merge `search_plan.v2` output into the deterministic proposals, keeping the guards."""
    by_variant = {
        str(raw.get("variant")): raw
        for raw in outputs
        if isinstance(raw, dict) and raw.get("variant")
    }
    merged: list[s.SearchProposal] = []
    for proposal in proposals:
        raw = by_variant.get(proposal.variant)
        if raw is None:
            merged.append(proposal)
            continue
        try:
            criteria = plan_from_model(_plan_output(raw), base=proposal.criteria)
        except Exception:
            merged.append(proposal)
            continue
        # Guards that hold even when the model proposes otherwise.
        role_skills = [*criteria.skills.must, *criteria.skills.nice]
        must = skill_rules.must_have(
            profile_skills=inp.profile_skills,
            role_skills=role_skills,
            experiences=inp.experiences,
        )
        nice = skill_rules.nice_to_have(
            profile_skills=inp.profile_skills,
            role_skills=role_skills,
            must=must,
        )
        base = proposal.criteria
        criteria = criteria.model_copy(
            update={
                "skills": SkillSets(must=must, nice=nice),
                "languages": [],
                "salary": None,
                "education": None,
                "clearance": None,
                # Personal filters stay as setup derived them; the model only shapes the role.
                "locations": base.locations,
                "remote_eligibility": RemoteEligibility(
                    anywhere=criteria.remote_eligibility.anywhere,
                    regions=list(criteria.remote_eligibility.regions),
                    countries=list(base.remote_eligibility.countries),
                    base_tz=base.remote_eligibility.base_tz,
                ),
                "visa_sponsorship": base.visa_sponsorship,
                "relocation": base.relocation,
                "min_match_score": base.min_match_score,
                "caps": base.caps,
                "keywords": base.keywords,
                "titles": [spec for spec in criteria.titles if not spec.exclude][:MAX_TITLES],
            }
        )
        merged.append(
            proposal.model_copy(
                update={
                    "criteria": criteria,
                    "summary": summarize(criteria),
                }
            )
        )
    return merged


def _plan_output(raw: dict[str, Any]):
    from app.tracks.plan import SearchPlanDraft

    return SearchPlanDraft.model_validate(
        {
            "titles": raw.get("titles") or [],
            "core_skills": raw.get("core_skills") or [],
            "nice_skills": raw.get("nice_skills") or [],
            "seniority": raw.get("seniority") or [],
            "employment_types": raw.get("employment_types") or [],
            "work_modes": raw.get("work_modes") or [],
            "regions": raw.get("regions") or [],
            "anywhere": bool(raw.get("anywhere")),
            "posting_max_age_days": raw.get("posting_max_age_days"),
            "exclude_agencies": bool(raw.get("exclude_agencies", True)),
        }
    )
