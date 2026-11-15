"""Industry pack schema: one declarative description of how the app behaves for a field of work.

Packs are code, versioned and reviewed. Components and services read the resolved manifest; they
never branch on the industry key. See `docs/architecture/industries.md`.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.tracks.criteria import EmploymentType, SalaryPeriod, Seniority, Shift, WorkMode

PackConfig = ConfigDict(frozen=True, extra="forbid")

Visibility = Literal["visible", "collapsed", "hidden"]
FacetKind = Literal["multi", "single", "bool", "range"]
FacetScope = Literal["criteria", "profile", "job"]

# Every criteria control a pack can show, collapse, or hide. Kept explicit so registry tests can
# prove each field has a state and appears in exactly one group.
CRITERIA_FIELDS: frozenset[str] = frozenset(
    {
        "titles",
        "occupations",
        "skills",
        "seniority",
        "employment_types",
        "work_modes",
        "shifts",
        "remote_eligibility",
        "locations",
        "visa_sponsorship",
        "relocation",
        "salary",
        "salary_includes",
        "facets",
        "companies",
        "posting_max_age_days",
        "languages",
        "education",
        "clearance",
        "keywords",
        "min_match_score",
    }
)

PROFILE_SECTIONS: frozenset[str] = frozenset(
    {"experience", "projects", "skills", "certifications", "education", "languages", "documents"}
)

MATCH_WEIGHTS: frozenset[str] = frozenset(
    {
        "title",
        "skills",
        "seniority",
        "salary",
        "freshness",
        "location",
        "semantic",
        "llm",
        "credentials",
        "shift",
    }
)

_SLUG = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


class FacetOption(BaseModel):
    model_config = PackConfig

    key: str
    label_key: str
    synonyms: tuple[str, ...] = ()

    @field_validator("key")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not _SLUG.match(v):
            raise ValueError("facet option key must be snake_case")
        return v


class FacetMatch(BaseModel):
    model_config = PackConfig

    filter: bool = False
    boost: float = Field(default=0.0, ge=0.0, le=0.5)
    ledger_only: bool = False


class FacetDef(BaseModel):
    """An industry-specific dimension (cuisine, station, kitchen type)."""

    model_config = PackConfig

    key: str
    label_key: str
    kind: FacetKind = "multi"
    options: tuple[FacetOption, ...] = ()
    applies_to: tuple[FacetScope, ...] = ("criteria", "job")
    match: FacetMatch = Field(default_factory=FacetMatch)
    group: str = "criteria"

    @field_validator("key")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not _SLUG.match(v):
            raise ValueError("facet key must be snake_case")
        return v

    @model_validator(mode="after")
    def _options_required(self):
        if self.kind in ("multi", "single") and not self.options:
            raise ValueError(f"facet {self.key!r} needs options")
        keys = [o.key for o in self.options]
        if len(keys) != len(set(keys)):
            raise ValueError(f"facet {self.key!r} has duplicate option keys")
        return self


class RoleFamily(BaseModel):
    """Second level of the field picker (Kitchen, Pastry and bakery, ...)."""

    model_config = PackConfig

    key: str
    label_key: str
    titles: tuple[str, ...] = ()


class Detection(BaseModel):
    model_config = PackConfig

    isco_groups: tuple[str, ...] = ()
    esco_prefixes: tuple[str, ...] = ()
    title_keywords: tuple[str, ...] = ()
    resume_cues: tuple[str, ...] = ()


class UiManifest(BaseModel):
    """Visibility, order, and labels. Missing state falls back to the General pack."""

    model_config = PackConfig

    groups: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    states: dict[str, Visibility] = Field(default_factory=dict)
    profile_sections: tuple[str, ...] = ()
    labels: dict[str, str] = Field(default_factory=dict)
    nav: dict[str, bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _known_fields(self):
        seen: set[str] = set()
        for group, fields in self.groups.items():
            if not group or len(group) > 32:
                raise ValueError("invalid criteria group id")
            for field_id in fields:
                if field_id not in CRITERIA_FIELDS:
                    raise ValueError(f"unknown criteria field: {field_id}")
                if field_id in seen:
                    raise ValueError(f"criteria field listed twice: {field_id}")
                seen.add(field_id)
        for field_id in self.states:
            if field_id not in CRITERIA_FIELDS:
                raise ValueError(f"unknown criteria field in states: {field_id}")
        for section in self.profile_sections:
            if section not in PROFILE_SECTIONS:
                raise ValueError(f"unknown profile section: {section}")
        return self


class CriteriaDefaults(BaseModel):
    model_config = PackConfig

    work_modes: tuple[WorkMode, ...] = ()
    employment_types: tuple[EmploymentType, ...] = ()
    shifts: tuple[Shift, ...] = ()
    salary_period: SalaryPeriod | None = None
    posting_max_age_days: int | None = Field(default=None, ge=1, le=365)


class LadderStep(BaseModel):
    """A local rank name mapped onto the shared Seniority scale."""

    model_config = PackConfig

    key: str
    label_key: str
    maps_to: Seniority
    aliases: tuple[str, ...] = ()


class CredentialDef(BaseModel):
    model_config = PackConfig

    key: str
    label_key: str
    aliases: tuple[str, ...] = ()
    countries: tuple[str, ...] = ()
    validity_months: int | None = Field(default=None, ge=1, le=600)
    knockout: bool = False


class AnswerKeyPlan(BaseModel):
    model_config = PackConfig

    add: tuple[str, ...] = ()
    hide: tuple[str, ...] = ()


class SourcePlan(BaseModel):
    model_config = PackConfig

    adapters: tuple[str, ...] = ()
    adzuna_categories: dict[str, str] = Field(default_factory=dict)
    query_templates: tuple[str, ...] = ()
    employer_tags: tuple[str, ...] = ()
    alert_sources: tuple[str, ...] = ()


class MatchingPlan(BaseModel):
    model_config = PackConfig

    weights: dict[str, float] = Field(default_factory=dict)
    generic_title_words: tuple[str, ...] = ()
    title_groups: tuple[tuple[str, ...], ...] = ()

    @field_validator("weights")
    @classmethod
    def _weights(cls, v: dict[str, float]) -> dict[str, float]:
        for key, value in v.items():
            if key not in MATCH_WEIGHTS:
                raise ValueError(f"unknown match weight: {key}")
            if not 0.0 <= float(value) <= 0.6:
                raise ValueError(f"match weight out of range: {key}")
        return v


class ProfilePlan(BaseModel):
    model_config = PackConfig

    section_order: tuple[str, ...] = ()
    labels: dict[str, str] = Field(default_factory=dict)
    gap_questions: tuple[str, ...] = ()
    gap_actions: tuple[str, ...] = ()
    evidence_metrics: tuple[str, ...] = ()
    completeness_items: tuple[str, ...] = ()
    found_checklist: tuple[str, ...] = ()
    interview_questions: tuple[str, ...] = ()
    trial_shift_checklist: tuple[str, ...] = ()


class ResumePlan(BaseModel):
    model_config = PackConfig

    template_id: str = "classic"
    section_order: tuple[str, ...] = ()
    section_titles: dict[str, str] = Field(default_factory=dict)
    photo_default: bool = False
    bullet_guidance: tuple[str, ...] = ()


class AiBrief(BaseModel):
    model_config = PackConfig

    brief: str = Field(default="", max_length=600)
    vocabulary: tuple[str, ...] = ()


class SafetyPlan(BaseModel):
    model_config = PackConfig

    signals: tuple[str, ...] = ()


class FeatureFlags(BaseModel):
    model_config = PackConfig

    be_found: bool = True
    github_links: bool = False
    coding_practice: bool = False
    portfolio_images: bool = False
    photo_resume: bool = False
    query_sources: bool = False


class IndustryPack(BaseModel):
    model_config = PackConfig

    key: str
    version: int = Field(default=1, ge=1)
    label_key: str
    display_name: str = Field(default="", max_length=80)
    icon: str = "ph:briefcase"
    detection: Detection = Field(default_factory=Detection)
    role_families: tuple[RoleFamily, ...] = ()
    ui: UiManifest = Field(default_factory=UiManifest)
    facets: tuple[FacetDef, ...] = ()
    criteria_defaults: CriteriaDefaults = Field(default_factory=CriteriaDefaults)
    seniority_ladder: tuple[LadderStep, ...] = ()
    credentials: tuple[CredentialDef, ...] = ()
    answer_keys: AnswerKeyPlan = Field(default_factory=AnswerKeyPlan)
    sources: SourcePlan = Field(default_factory=SourcePlan)
    matching: MatchingPlan = Field(default_factory=MatchingPlan)
    profile: ProfilePlan = Field(default_factory=ProfilePlan)
    resume: ResumePlan = Field(default_factory=ResumePlan)
    ai: AiBrief = Field(default_factory=AiBrief)
    safety: SafetyPlan = Field(default_factory=SafetyPlan)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    @field_validator("key")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not _SLUG.match(v):
            raise ValueError("pack key must be snake_case")
        return v

    @model_validator(mode="after")
    def _unique_children(self):
        for name in ("facets", "role_families", "credentials", "seniority_ladder"):
            keys = [item.key for item in getattr(self, name)]
            if len(keys) != len(set(keys)):
                raise ValueError(f"duplicate {name} key in pack {self.key}")
        return self
