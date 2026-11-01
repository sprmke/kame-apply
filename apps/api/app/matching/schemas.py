"""Matching API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BoardJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    track_id: uuid.UUID
    job_id: uuid.UUID
    score: float | None = None
    status: str
    eligibility: str
    reasons: list[Any] = Field(default_factory=list)
    score_components: dict[str, Any] = Field(default_factory=dict)
    ai_review_paused: bool = False
    skip_reason: str | None = None
    seen_at: datetime | None = None
    title: str | None = None
    company_name: str | None = None
    company_id: uuid.UUID | None = None
    apply_url: str | None = None
    canonical_url: str | None = None
    work_mode: str | None = None
    locations: list[Any] = Field(default_factory=list)
    salary: dict[str, Any] = Field(default_factory=dict)
    posted_at: datetime | None = None
    risk_level: str | None = None


class OtherRoleRead(BaseModel):
    id: uuid.UUID
    title: str
    apply_url: str


class JobDetailRead(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    job_id: uuid.UUID
    score: float | None = None
    status: str
    eligibility: str
    eligibility_quote: str | None = None
    eligibility_detail: dict[str, Any] = Field(default_factory=dict)
    reasons: list[Any] = Field(default_factory=list)
    score_components: dict[str, Any] = Field(default_factory=dict)
    fit: dict[str, Any] = Field(default_factory=dict)
    ai_review_paused: bool = False
    title: str
    company_name: str | None = None
    company_id: uuid.UUID | None = None
    apply_url: str
    canonical_url: str
    work_mode: str | None = None
    locations: list[Any] = Field(default_factory=list)
    salary: dict[str, Any] = Field(default_factory=dict)
    posted_at: datetime | None = None
    description_html: str = ""
    description_text: str = ""
    few_stated_requirements: bool = False
    qualifications: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    other_roles: list[OtherRoleRead] = Field(default_factory=list)
    risk_level: str | None = None
    risk_reasons: list[Any] = Field(default_factory=list)


class TriageBody(BaseModel):
    action: Literal["shortlist", "skip", "hide", "applied", "restore"]
    skip_reason: str | None = Field(default=None, max_length=200)


class HideCompanyBody(BaseModel):
    company_id: uuid.UUID
    track_id: uuid.UUID | None = None
    reason: str = Field(default="", max_length=500)


class ScoreResultRead(BaseModel):
    scored: int
    eligible: int


class RelaxationRead(BaseModel):
    label: str
    gained: int
    total: int


class OkRead(BaseModel):
    ok: bool = True
