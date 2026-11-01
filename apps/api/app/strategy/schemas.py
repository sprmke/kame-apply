from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class SuggestionBlock(BaseModel):
    kind: str
    text: str
    why: str
    char_count: int = 0


class LinkedInOptimizeRead(BaseModel):
    track_id: uuid.UUID
    headline: SuggestionBlock
    about: SuggestionBlock
    skills_order: list[str]
    skills_why: str
    experience: list[SuggestionBlock]
    open_to_work: list[str]
    github_checklist: list[str]


class ConsistencyIssue(BaseModel):
    field: str
    severity: Literal["info", "warn", "error"]
    message: str
    fix: str


class ConsistencyReport(BaseModel):
    issues: list[ConsistencyIssue]
    score: int = Field(ge=0, le=100)


class ConsistencyBody(BaseModel):
    linkedin_text: str = Field(min_length=20, max_length=100_000)
    track_id: uuid.UUID | None = None


class CapCheckRead(BaseModel):
    company_name: str
    active_count: int
    cap: int
    window_days: int
    exceeds: bool
    warn: bool
    message: str


class FreshnessRead(BaseModel):
    job_id: uuid.UUID
    label: str
    hours_ago: float | None
    boost: Literal["high", "medium", "low", "none"]


class SalaryAdviceRead(BaseModel):
    posting_min: float | None
    posting_max: float | None
    posting_currency: str | None
    market_p50: float | None
    user_floor: float | None
    suggested_min: float | None
    suggested_max: float | None
    currency: str
    rationale: str
    truthful: bool = True


class FollowUpDraftsRead(BaseModel):
    day_7: str
    day_14: str


class StrategyPrefRead(BaseModel):
    company_cap: int = 3
    company_cap_window_days: int = 90


class StrategyPrefUpdate(BaseModel):
    company_cap: int = Field(default=3, ge=1, le=20)
    company_cap_window_days: int = Field(default=90, ge=7, le=365)


class OkRead(BaseModel):
    ok: bool = True
    detail: dict[str, Any] = Field(default_factory=dict)
