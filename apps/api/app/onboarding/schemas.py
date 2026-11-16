"""Onboarding request and response schemas.

`POST /onboarding/plan` is the legacy request-scoped plan. `/onboarding/setups/*` persists a
draft so the user can review it, retry it with AI, and undo it later.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.tracks.criteria import CriteriaV1, TitleSpec

SetupSubject = Literal["self", "other_person"]
SetupMode = Literal["new", "update"]
SetupStatus = Literal[
    "queued",
    "running",
    "ready",
    "applying",
    "applied",
    "failed",
    "cancelled",
    "discarded",
    "expired",
    "reverted",
]
SetupGroup = Literal["profile", "answers", "writing", "searches", "studio", "account", "industry"]
ItemKind = Literal["value", "list", "entity", "search"]
ItemAction = Literal["add", "fill_blank", "replace", "keep_current", "skip"]
ItemSource = Literal["resume", "you_said", "suggested", "default"]
ItemBlocked = Literal["ok", "role", "other_person", "limit", "duplicate"]
SeenPage = Literal["profile", "answers", "writing", "searches", "studio", "account"]


class OnboardingPlanBody(BaseModel):
    resume_text: str | None = Field(default=None, max_length=20_000)
    role_text: str | None = Field(default=None, max_length=8000)
    profile_id: str | None = None
    timezone: str = Field(default="UTC", max_length=64)


class ResumeBasics(BaseModel):
    name: str = ""
    email: str = ""
    headline: str = ""
    location: str = ""
    country: str = ""
    skills: list[str] = Field(default_factory=list)
    years: int | None = None


class ScheduleDefaults(BaseModel):
    preset: str = "every_4_hours"
    timezone: str = "UTC"
    quiet_hours: dict[str, str] = Field(default_factory=lambda: {"start": "22:00", "end": "07:00"})
    daily_cap: int = 12


class OnboardingPlanRead(BaseModel):
    basics: ResumeBasics
    answers: list[dict[str, Any]] = Field(default_factory=list)
    search: dict[str, Any] | None = None
    schedule: ScheduleDefaults
    source: Literal["defaults", "ai"] = "defaults"


# ---- setup drafts -----------------------------------------------------------------------------


class SetupCreate(BaseModel):
    """Start a draft from an uploaded document or pasted text.

    A file is uploaded through `POST /profiles/{id}/documents` first; the draft takes that
    document id. Exactly one of `document_id` and `text` is required.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID | None = None
    text: str | None = Field(default=None, min_length=200, max_length=60_000)
    role_text: str | None = Field(default=None, max_length=2000)
    timezone: str = Field(default="UTC", max_length=64)
    subject: SetupSubject = "self"
    profile_id: uuid.UUID | None = None
    mode: SetupMode | None = None
    with_ai: bool = True

    @model_validator(mode="after")
    def _one_source(self):
        if (self.document_id is None) == (self.text is None):
            raise ValueError("send exactly one of document_id or text")
        return self


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID
    quote: str = Field(min_length=1, max_length=200)
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)


class SetupItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    group: SetupGroup
    target: str = Field(min_length=1, max_length=200)
    kind: ItemKind
    value: Any = None
    current: Any = None
    current_id: uuid.UUID | None = None
    action: ItemAction = "add"
    source: ItemSource
    confidence: float = Field(default=1.0, ge=0, le=1)
    evidence: list[EvidenceRef] = Field(default_factory=list, max_length=20)
    reason_key: str = Field(min_length=1, max_length=120)
    reason_params: dict[str, str | int] = Field(default_factory=dict)
    needs_you: bool = False
    blocked: ItemBlocked = "ok"
    default_on: bool = True

    @model_validator(mode="after")
    def _needs_you_is_empty(self):
        """A needs-you row is a question. A prefilled value would read as an answer we guessed."""
        if self.needs_you and self.value not in (None, "", [], {}):
            raise ValueError("a needs-you item cannot carry a value")
        return self


class SalaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float = Field(gt=0, le=10_000_000)
    currency: str = Field(min_length=3, max_length=3)
    period: Literal["hour", "day", "month", "year"] = "month"

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, value: str) -> str:
        return value.upper()


class SearchProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Literal["you_said", "same_role", "step_up"]
    name: str = Field(min_length=1, max_length=200)
    nl_text: str = Field(min_length=1, max_length=2000)
    criteria: CriteriaV1
    summary: str = ""
    autonomy: Literal["discover", "prepare", "assist"] = "prepare"
    schedule: ScheduleDefaults
    duplicate_of: uuid.UUID | None = None
    blocked: Literal["ok", "limit", "duplicate"] = "ok"
    default_on: bool = True
    adjacent_titles: list[str] = Field(default_factory=list, max_length=10)


class IndustryHint(BaseModel):
    """The field of work the resume points at. A chip on the review, never a silent switch."""

    model_config = ConfigDict(extra="forbid")

    pack_key: str = Field(min_length=1, max_length=48)
    label_key: str = Field(default="", max_length=120)
    role_family: str | None = Field(default=None, max_length=48)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SetupBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    items: list[SetupItem] = Field(default_factory=list, max_length=600)
    searches: list[SearchProposal] = Field(default_factory=list, max_length=3)
    profile_merge: dict[str, Any] | None = None
    notices: list[str] = Field(default_factory=list, max_length=20)
    counts: dict[str, int] = Field(default_factory=dict)
    lowest_pay: SalaryInput | None = None
    industry: IndustryHint | None = None

    @model_validator(mode="after")
    def _unique_ids(self):
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("item ids must be unique")
        return self


class ItemDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ItemAction = "add"
    value: Any = None
    edited: bool = False


class SetupDecisions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: dict[str, ItemDecision] = Field(default_factory=dict)
    searches: dict[str, SearchProposal] = Field(default_factory=dict)
    lowest_pay: SalaryInput | None = None
    lowest_pay_set: bool = False
    seen_pages: list[SeenPage] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _bounded(self):
        if len(self.items) > 600:
            raise ValueError("too many item decisions")
        for key in self.items:
            if not key or len(key) > 200:
                raise ValueError("invalid item id")
        if len(self.searches) > 3:
            raise ValueError("too many search overrides")
        for variant in self.searches:
            if variant not in {"you_said", "same_role", "step_up"}:
                raise ValueError("invalid search variant")
        return self


class SetupRetry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    with_ai: bool = False


class SetupSeen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: SeenPage


class SetupApplyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_first_run: bool = True


class SetupValidateRead(BaseModel):
    ok: bool
    errors: dict[str, str] = Field(default_factory=dict)


class SetupApplyRead(BaseModel):
    draft_id: uuid.UUID
    profile_id: uuid.UUID
    applied_at: datetime
    created: dict[str, list[uuid.UUID]] = Field(default_factory=dict)
    updated: dict[str, list[uuid.UUID]] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)
    links: dict[str, str] = Field(default_factory=dict)


class SetupStepRead(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str = "pending"
    source: Literal["ai", "rules", "skipped"] | None = None
    reason: str | None = None


class SetupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    profile_id: uuid.UUID
    document_id: uuid.UUID | None
    subject: SetupSubject
    mode: SetupMode
    status: SetupStatus
    role_text: str | None
    steps: dict[str, Any] = Field(default_factory=dict)
    bundle: SetupBundle | None = None
    decisions: SetupDecisions = Field(default_factory=SetupDecisions)
    error_code: str | None = None
    expires_at: datetime | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SetupProvenanceRead(BaseModel):
    draft_id: uuid.UUID
    profile_id: uuid.UUID
    applied_at: datetime
    created: dict[str, list[uuid.UUID]] = Field(default_factory=dict)
    updated: dict[str, list[uuid.UUID]] = Field(default_factory=dict)
    seen_pages: list[SeenPage] = Field(default_factory=list)


class SetupRevertRead(BaseModel):
    draft_id: uuid.UUID
    removed: dict[str, int] = Field(default_factory=dict)
    kept: list[dict[str, str]] = Field(default_factory=list)


# ---- model output contracts (tool-less calls) -------------------------------------------------


class StatedSignalOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["notice", "salary", "relocation", "work_authorization", "sponsorship", "remote"]
    value: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=1, max_length=200)
    country: str | None = Field(default=None, max_length=2)
    confidence: float = Field(default=0.7, ge=0, le=1)


class SetupSignalsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signals: list[StatedSignalOut] = Field(default_factory=list, max_length=12)


class SearchVariantOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Literal["you_said", "same_role", "step_up"]
    name: str = Field(default="", max_length=200)
    titles: list[TitleSpec] = Field(default_factory=list, max_length=5)
    core_skills: list[str] = Field(default_factory=list, max_length=6)
    nice_skills: list[str] = Field(default_factory=list, max_length=10)
    seniority: list[str] = Field(default_factory=list, max_length=4)
    employment_types: list[str] = Field(default_factory=list, max_length=6)
    work_modes: list[str] = Field(default_factory=list, max_length=3)
    regions: list[str] = Field(default_factory=list, max_length=4)
    anywhere: bool = False
    posting_max_age_days: int | None = Field(default=None, ge=1, le=90)
    exclude_agencies: bool = True


class SearchPlanV2Out(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variants: list[SearchVariantOut] = Field(default_factory=list, max_length=3)
