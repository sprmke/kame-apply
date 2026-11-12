"""Search plan: turn a role description into a complete, editable search setup.

Two layers, one result:

- A deterministic, pack-aware baseline fills role-typical titles, skills, work modes,
  shifts, and salary period from the field of work, so a chef gets kitchen defaults
  and an engineer gets software defaults.
- AI may enrich that baseline (titles, skills, seniority) when it is configured.

This is deliberately different from `compile_nl`: the compiler only extracts what the text
says, while a plan fills in role-typical settings so a new search works without the user
hand-building every field. Suggestions are still drafts: the UI shows them as chips the
user can remove before saving.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import PromptedOutput

from app.ai import service as ai
from app.ai.prompts import SEARCH_PLAN
from app.core.config import Settings
from app.core.security import WorkspaceContext
from app.industries.detect import IndustryDetection, detect_industry
from app.industries.packs.general import GENERAL
from app.industries.registry import get_pack
from app.industries.schema import IndustryPack
from app.sources.search_service import plan_queries
from app.taxonomy.aliases import SKILL_ALIASES
from app.taxonomy.seed import SKILLS
from app.tracks.criteria import (
    CompanyFilter,
    CriteriaV1,
    RemoteEligibility,
    SalaryFilter,
    SkillSets,
    TitleSpec,
    empty_criteria,
)
from app.tracks.diff import diff_criteria
from app.tracks.models import Track
from app.tracks.summary import summarize
from app.tracks.validate import validate_criteria

FEATURE = "search_plan"
TIER = "standard"
PROMPT = SEARCH_PLAN

MAX_OUT = 1600

_SENIORITY = {
    "intern": "intern",
    "internship": "intern",
    "junior": "junior",
    "entry": "junior",
    "mid": "mid",
    "senior": "senior",
    "staff": "staff",
    "principal": "principal",
    "lead": "lead",
    "manager": "manager",
    "director": "director",
    "executive": "executive",
}
_EMPLOYMENT = {
    "full_time": "full_time",
    "full-time": "full_time",
    "full time": "full_time",
    "part_time": "part_time",
    "part-time": "part_time",
    "part time": "part_time",
    "contract": "contract",
    "contractor": "contract",
    "freelance": "freelance",
    "internship": "internship",
    "intern": "internship",
    "temporary": "temporary",
}
_WORK_MODES = {
    "remote": "remote",
    "hybrid": "hybrid",
    "on_site": "on_site",
    "on-site": "on_site",
    "onsite": "on_site",
    "office": "on_site",
}
_SHIFTS = {
    "morning": "morning",
    "morning shift": "morning",
    "afternoon": "afternoon",
    "evening": "evening",
    "evening shift": "evening",
    "night": "night",
    "night shift": "night",
    "rotating": "rotating",
    "rotating shift": "rotating",
    "split": "split",
    "split shift": "split",
    "weekend": "weekend",
    "weekends": "weekend",
}
_REGIONS = {"APAC", "EU", "LATAM", "MENA", "NA", "AFRICA"}

_STOP = frozenset("a an and at for in of on or the to with".split())
# Role words that appear in almost every template name; they cannot carry a match alone.
_GENERIC_TITLE = frozenset(
    "engineer engineering developer manager specialist senior junior lead staff principal "
    "full stack time part remote hybrid".split()
)

# Small bootstrap vocabulary so a deterministic plan honours skills named in the brief.
_SKILL_WORDS: dict[str, str] = dict(SKILL_ALIASES)
for _row in SKILLS:
    _label = str(_row.get("label") or "")
    if _label:
        _SKILL_WORDS[_label.casefold()] = _label
    for _alias in _row.get("aliases") or []:
        _SKILL_WORDS[str(_alias).casefold()] = _label

_TITLE_PREFIX = re.compile(
    r"^(?:i\s+am|i'm|we\s+are|looking\s+for|seeking|searching\s+for|a|an|the)\s+",
    re.I,
)
# Title fragments that mark the end of the role name in a plain sentence.
_TITLE_STOP = re.compile(
    r"\s+\b(remote|hybrid|on[- ]?site|in[- ]office|full[- ]time|part[- ]time|contract|"
    r"freelance|internship|temporary)\b.*$",
    re.I,
)
_TITLE_PLACE = re.compile(
    r"\s+\b(in|at|near|within|across|around)\s+.*$",
    re.I,
)
_TITLE_NOUN = re.compile(
    r"\s+\b(roles?|jobs?|positions?|openings?|opportunities|vacancies)\b\s*$",
    re.I,
)
_WORD = re.compile(r"[a-z0-9+#.]+")


class SearchPlanIn(BaseModel):
    """Request body for a plan. Industry is optional: it is detected when omitted."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=8000)
    industry: str | None = Field(default=None, max_length=48)


class SearchPlanDraft(BaseModel):
    """Model output. Validated by pydantic_ai before we touch CriteriaV1."""

    model_config = ConfigDict(extra="forbid")

    titles: list[TitleSpec] = Field(default_factory=list)
    core_skills: list[str] = Field(default_factory=list)
    nice_skills: list[str] = Field(default_factory=list)
    seniority: list[str] = Field(default_factory=list)
    employment_types: list[str] = Field(default_factory=list)
    work_modes: list[str] = Field(default_factory=list)
    shifts: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    anywhere: bool = False
    posting_max_age_days: int | None = None
    exclude_agencies: bool = True


class SearchPlanQuery(BaseModel):
    keywords: str
    location: str = ""
    country: str = ""
    category: str | None = None


class SearchPlanOut(BaseModel):
    """Draft search setup plus the pack it was built for and the queries it will run."""

    criteria: CriteriaV1
    summary: str
    diff: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    source: Literal["ai", "defaults"] = "defaults"
    ai_error: str | None = None
    name: str = ""
    prompt_version: str = ""
    provider: str | None = None
    model: str | None = None
    industry: str = GENERAL.key
    industry_version: int = 1
    role_family: str | None = None
    confidence: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    source_queries: list[SearchPlanQuery] = Field(default_factory=list)


class StructuredRunner(Protocol):
    async def __call__(self, ctx: WorkspaceContext, settings: Settings, **kwargs: Any) -> Any: ...


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(_fold(text)) if w not in _STOP}


def _delimit(text: str) -> str:
    return f"<<<UNTRUSTED_ROLE_TEXT>>>\n{text.strip()}\n<<<END_UNTRUSTED_ROLE_TEXT>>>"


def _clean_list(items: Sequence[str], *, limit: int, skip: set[str] | None = None) -> list[str]:
    out: list[str] = []
    seen = set(skip or ())
    for raw in items:
        value = " ".join(str(raw).split()).strip(" .,;:")
        if not value or len(value) > 80:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
        if len(out) >= limit:
            break
    return out


def _pick(items: Sequence[str], mapping: dict[str, str]) -> list[str]:
    out: list[str] = []
    for raw in items:
        value = mapping.get(str(raw).strip().casefold())
        if value and value not in out:
            out.append(value)
    return out


def _extract_title(text: str) -> str:
    first = re.split(r"[,.;\n|]", text.strip(), maxsplit=1)[0].strip()
    while _TITLE_PREFIX.match(first):
        first = _TITLE_PREFIX.sub("", first, count=1).strip()
    # "Customer support lead roles in the Philippines, remote" → "Customer support lead"
    mode = _TITLE_STOP.search(first)
    if mode and mode.start() > 0:
        first = first[: mode.start()]
    place = _TITLE_PLACE.search(first)
    if place and place.start() > 0:
        first = first[: place.start()]
    while _TITLE_NOUN.search(first):
        first = _TITLE_NOUN.sub("", first, count=1).strip()
    first = first.strip(" -:")
    words = first.split()
    if len(words) > 8:
        first = " ".join(words[:8])
    return first[:120].strip() or "Role"


def _pick_template(text: str, templates: Sequence[Any]) -> Any | None:
    body = _tokens(text) - _GENERIC_TITLE
    folded = _fold(text)
    if not body:
        return None
    best: Any | None = None
    best_score = 0.0
    for tmpl in templates:
        name = _fold(getattr(tmpl, "name", "") or "")
        if not name:
            continue
        if name in folded:
            return tmpl
        tokens = _tokens(name) - _GENERIC_TITLE
        if not tokens:
            continue
        shared = tokens & body
        score = len(shared) / len(tokens)
        if len(shared) >= 2 and score > best_score:
            best, best_score = tmpl, score
    return best if best_score >= 0.6 else None


def _mentioned_skills(text: str) -> list[str]:
    body = _fold(text)
    hits: list[tuple[int, str]] = []
    seen: set[str] = set()
    for word, canonical in _SKILL_WORDS.items():
        match = re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", body)
        if match is None or canonical.casefold() in seen:
            continue
        seen.add(canonical.casefold())
        hits.append((match.start(), canonical))
    hits.sort()
    return [name for _, name in hits]


def _pack_titles(text: str, pack: IndustryPack) -> list[str]:
    """Titles the pack knows that appear in the description, longest first."""
    lowered = _fold(text)
    hits = [
        title
        for family in pack.role_families
        for title in family.titles
        if title and _fold(title) in lowered
    ]
    hits.sort(key=len, reverse=True)
    return hits


def baseline(
    text: str, templates: Sequence[Any] = (), *, industry: str | None = None
) -> tuple[CriteriaV1, IndustryDetection, IndustryPack]:
    """Deterministic, pack-aware plan. Also the base the model may enrich."""
    detection = detect_industry(text)
    key = industry or detection.pack_key or GENERAL.key
    pack = get_pack(key) or GENERAL
    if industry and industry != detection.pack_key:
        detection = IndustryDetection(
            pack_key=industry,
            role_family=detection.role_family,
            confidence=detection.confidence,
            reasons=[*detection.reasons, f"field chosen by the user: {industry}"],
        )

    body = _fold(text.replace("-", " "))
    tmpl = _pick_template(text, templates)
    title = _extract_title(text)

    titles: list[TitleSpec] = [TitleSpec(title=title)]
    for pack_title in _pack_titles(text, pack):
        if pack_title.casefold() != title.casefold():
            titles.append(TitleSpec(title=pack_title))
        if len(titles) >= 5:
            break

    mentioned = _mentioned_skills(text)
    must: list[str] = []
    if tmpl is not None:
        tmpl_criteria = getattr(tmpl, "criteria", None) or {}
        for spec in tmpl_criteria.get("titles") or []:
            t = str(spec.get("title") or "").strip()
            if t and all(t.casefold() != existing.title.casefold() for existing in titles):
                titles.append(TitleSpec(title=t))
        if not mentioned:
            skills = tmpl_criteria.get("skills") or {}
            must = _clean_list(skills.get("must") or [], limit=6)
    must = _clean_list([*mentioned, *must], limit=6)

    work_modes = []
    if re.search(r"\bremote\b", body):
        work_modes.append("remote")
    if re.search(r"\bhybrid\b", body):
        work_modes.append("hybrid")
    if re.search(r"\b(on site|onsite|in office|office based)\b", body):
        work_modes.append("on_site")

    employment = []
    if re.search(r"\bfull time\b|\bpermanent\b", body):
        employment.append("full_time")
    if re.search(r"\bpart time\b", body):
        employment.append("part_time")
    if re.search(r"\bcontract\b", body):
        employment.append("contract")
    if re.search(r"\b(freelance|freelancer)\b", body):
        employment.append("freelance")
    if re.search(r"\binternship\b|\bintern\b", body):
        employment.append("internship")
    if re.search(r"\btemporary\b|\btemp\b", body):
        employment.append("temporary")

    shifts = _pick([word for word in _SHIFTS if re.search(rf"\b{word}\b", body)], _SHIFTS)

    seniority = []
    for word, level in _SENIORITY.items():
        if re.search(rf"\b{re.escape(word)}\b", body) and level not in seniority:
            seniority.append(level)

    regions = [r for r in _REGIONS if re.search(rf"\b{re.escape(r.lower())}\b", body)]
    anywhere = bool(re.search(r"\b(worldwide|anywhere|global)\b", body))

    age = 21
    if re.search(r"\b(last week|this week|past week)\b", body):
        age = 7
    elif re.search(r"\b(last month|past month)\b", body):
        age = 30

    visa = True if re.search(r"\b(visa|sponsor(ship|ed)?)\b", body) else None
    relocation = True if re.search(r"\b(relocat(e|ion|ing))\b", body) else None

    # Field defaults fill only what the description did not say, so an explicit
    # "remote" or "part time" always wins over the pack.
    defaults = pack.criteria_defaults
    if not work_modes:
        work_modes = list(defaults.work_modes)
    if not employment:
        employment = list(defaults.employment_types)
    if not shifts:
        shifts = list(defaults.shifts)
    if not age and defaults.posting_max_age_days:
        age = defaults.posting_max_age_days
    salary = SalaryFilter(period=defaults.salary_period) if defaults.salary_period else None

    return (
        CriteriaV1(
            titles=titles[:5],
            skills=SkillSets(must=must),
            seniority=seniority,  # type: ignore[arg-type]
            employment_types=employment,  # type: ignore[arg-type]
            work_modes=work_modes,  # type: ignore[arg-type]
            shifts=shifts,  # type: ignore[arg-type]
            remote_eligibility=RemoteEligibility(anywhere=anywhere, regions=regions),
            salary=salary,
            posting_max_age_days=age or 21,
            visa_sponsorship=visa,
            relocation=relocation,
            companies=CompanyFilter(exclude_agencies=True),
        ),
        detection,
        pack,
    )


def _from_model(plan: SearchPlanDraft, *, base: CriteriaV1) -> CriteriaV1:
    """Map model output onto CriteriaV1, falling back to the deterministic base when thin."""
    titles: list[TitleSpec] = []
    seen: set[str] = set()
    for spec in plan.titles:
        title = " ".join(spec.title.split()).strip()
        key = title.casefold()
        if not title or key in seen or len(title) > 120:
            continue
        seen.add(key)
        synonyms = _clean_list(spec.synonyms, limit=4, skip={key})
        titles.append(TitleSpec(title=title, synonyms=synonyms, exclude=spec.exclude))
        if len(titles) >= 5:
            break
    if not any(not t.exclude for t in titles):
        titles = list(base.titles)

    core = _clean_list(plan.core_skills, limit=6)
    nice = _clean_list(plan.nice_skills, limit=10, skip={c.casefold() for c in core})

    regions = [r.upper() for r in plan.regions if r.upper() in _REGIONS]
    anywhere = bool(plan.anywhere)
    if anywhere:
        regions = []

    age = plan.posting_max_age_days if plan.posting_max_age_days is not None else 21
    age = max(1, min(90, int(age)))

    data = base.model_dump(mode="json")
    data.update(
        {
            "titles": [t.model_dump(mode="json") for t in titles],
            "skills": {
                "must": core,
                "nice": nice,
                "exclude": list(base.skills.exclude),
            },
            "seniority": _pick(plan.seniority, _SENIORITY),
            "employment_types": _pick(plan.employment_types, _EMPLOYMENT),
            "work_modes": _pick(plan.work_modes, _WORK_MODES),
            "shifts": _pick(plan.shifts, _SHIFTS) or list(base.shifts),
            "remote_eligibility": {"anywhere": anywhere, "regions": regions},
            "posting_max_age_days": age,
            "companies": {
                **base.companies.model_dump(mode="json"),
                "exclude_agencies": plan.exclude_agencies,
            },
        }
    )
    return CriteriaV1.model_validate(data)


_FRESHNESS = re.compile(r"\b(post(ed)?|fresh|days? old|last (week|month)|this week)\b", re.I)
_AGENCIES = re.compile(r"\b(agenc(y|ies)|recruiter|staffing)\b", re.I)
_MODES = re.compile(r"\b(remote|hybrid|on[- ]?site|in[- ]office|office[- ]based)\b", re.I)
_REGION = re.compile(
    r"\b(apac|eu|europe|latam|latin america|mena|middle east|north america|africa|"
    r"worldwide|anywhere|global)\b",
    re.I,
)
_USER_MENTION = {
    "visa_sponsorship": re.compile(r"\b(visa|sponsor(ship|ed)?)\b", re.I),
    "relocation": re.compile(r"\brelocat(e|ion|ing)\b", re.I),
}


def _compose(current: CriteriaV1 | None, plan: CriteriaV1, text: str) -> CriteriaV1:
    """Role-shaped fields come from the plan; personal filters stay as the user set them."""
    if current is None:
        return plan

    data = current.model_dump(mode="json")
    planned = plan.model_dump(mode="json")

    excluded_titles = [t for t in current.titles if t.exclude]
    data["titles"] = [
        {**t.model_dump(mode="json"), "exclude": False} for t in plan.titles if not t.exclude
    ] + [t.model_dump(mode="json") for t in excluded_titles]

    excluded_skills = list(current.skills.exclude)
    data["skills"] = {
        "must": [s for s in planned["skills"]["must"] if s not in excluded_skills],
        "nice": [s for s in planned["skills"]["nice"] if s not in excluded_skills],
        "exclude": excluded_skills,
    }

    # Only replace a filter when the description actually speaks to it, so a plain
    # "senior engineer" does not quietly wipe a user's hybrid-only or 7-day settings.
    if plan.seniority:
        data["seniority"] = planned["seniority"]
    if plan.employment_types:
        data["employment_types"] = planned["employment_types"]
    if plan.work_modes or _MODES.search(text):
        data["work_modes"] = planned["work_modes"]
    if plan.shifts and not current.shifts:
        data["shifts"] = planned["shifts"]

    remote = dict(data["remote_eligibility"])
    region_unset = (
        not remote.get("anywhere") and not remote.get("regions") and not remote.get("countries")
    )
    if _REGION.search(text) or region_unset:
        remote["anywhere"] = planned["remote_eligibility"]["anywhere"]
        remote["regions"] = planned["remote_eligibility"]["regions"]
    data["remote_eligibility"] = remote

    if data.get("posting_max_age_days") is None or _FRESHNESS.search(text):
        data["posting_max_age_days"] = planned["posting_max_age_days"]
    if not data["companies"].get("exclude_agencies") or _AGENCIES.search(text):
        data["companies"]["exclude_agencies"] = planned["companies"]["exclude_agencies"]

    # Sponsorship and relocation are personal constraints. Only override on an explicit mention.
    if _USER_MENTION["visa_sponsorship"].search(text):
        data["visa_sponsorship"] = True
    if _USER_MENTION["relocation"].search(text):
        data["relocation"] = True

    return CriteriaV1.model_validate(data)


def _suggested_name(criteria: CriteriaV1) -> str:
    for spec in criteria.titles:
        if not spec.exclude:
            return spec.title[:80]
    return "Search"


def _baseline(text: str, templates: Sequence[Any] = ()) -> CriteriaV1:
    """Criteria-only baseline, kept for evals and callers that do not need pack context."""
    return baseline(text, templates)[0]


def _queries(criteria: CriteriaV1, pack: IndustryPack) -> list[SearchPlanQuery]:
    track = Track(name=_suggested_name(criteria), industry=pack.key)
    rows = plan_queries(track, criteria, pack, limit=6)
    return [
        SearchPlanQuery(
            keywords=str(row.get("keywords") or ""),
            location=str(row.get("location") or ""),
            country=str(row.get("country") or ""),
            category=row.get("category"),
        )
        for row in rows
    ]


def plan_search(
    body: SearchPlanIn, templates: Sequence[Any] = ()
) -> tuple[CriteriaV1, IndustryDetection, IndustryPack]:
    """Deterministic plan for the given text and optional field of work."""
    return baseline(body.text, templates, industry=body.industry)


async def generate_plan(
    ctx: WorkspaceContext,
    settings: Settings | None,
    *,
    text: str,
    templates: Sequence[Any] = (),
    current: CriteriaV1 | None = None,
    industry: str | None = None,
    run_structured: StructuredRunner | None = None,
    model_factory=None,
) -> dict[str, Any]:
    """Build a full search setup. Falls back to deterministic defaults when AI is unavailable."""
    base_criteria, detection, pack = baseline(text, templates, industry=industry)
    source: Literal["ai", "defaults"] = "defaults"
    ai_error: str | None = None
    provider = model = None

    runner = run_structured or (ai.run_structured if settings is not None else None)
    if runner is not None and settings is not None:
        kwargs: dict[str, Any] = {
            "tier": TIER,
            "feature": FEATURE,
            "system": PROMPT.system,
            "prompt": _delimit(text),
            "output_type": PromptedOutput(SearchPlanDraft),
            "max_output_tokens": MAX_OUT,
        }
        if model_factory is not None:
            kwargs["model_factory"] = model_factory
        try:
            result = await runner(ctx, settings, **kwargs)
            plan = _from_model(result.output, base=base_criteria)
            source = "ai"
            provider = getattr(result, "provider", None)
            model = getattr(result, "model", None)
        except Exception as exc:  # AI is an enhancement; a search must still be usable.
            ai_error = getattr(exc, "code", None) or type(exc).__name__
            plan = base_criteria
            if ai_error not in {"ai_not_configured", "budget_reached"}:
                import structlog

                structlog.get_logger().warning("search_plan_failed", error=str(exc)[:200])
    else:
        ai_error = "ai_not_configured"
        plan = base_criteria

    criteria = _compose(current, plan, text)
    name = _suggested_name(criteria)
    return {
        "criteria": criteria,
        "summary": summarize(criteria),
        "diff": diff_criteria(current or empty_criteria(), criteria),
        "warnings": validate_criteria(criteria),
        "source": source,
        "ai_error": ai_error,
        "name": name,
        "titles": [t.title for t in criteria.titles if not t.exclude][:5] or [name],
        "prompt_version": PROMPT.key,
        "provider": provider,
        "model": model,
        "industry": pack.key,
        "industry_version": pack.version,
        "role_family": detection.role_family,
        "confidence": detection.confidence,
        "reasons": detection.reasons,
        "source_queries": _queries(criteria, pack),
    }
