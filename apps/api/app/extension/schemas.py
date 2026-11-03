"""Pydantic schemas for extension API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExtensionTokenCreate(BaseModel):
    label: str = "browser"
    scopes: list[str] = Field(default_factory=lambda: ["extension"])


class ExtensionTokenCreated(BaseModel):
    id: uuid.UUID
    token: str
    label: str
    scopes: list[str]
    expires_at: datetime | None


class ExtensionTokenRead(BaseModel):
    id: uuid.UUID
    label: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None


class PlatformPolicyRead(BaseModel):
    platform: str
    autofill_enabled: bool
    terms_acknowledged_at: datetime | None


class PlatformPolicyPut(BaseModel):
    platform: str
    autofill_enabled: bool
    acknowledge_terms: bool = False


class ClipBody(BaseModel):
    url: str
    title: str = ""
    company: str = ""
    description_text: str = ""
    json_ld: dict[str, Any] | None = None
    track_id: uuid.UUID | None = None
    platform: str = "generic"


class ClipResult(BaseModel):
    job_id: uuid.UUID
    track_job_id: uuid.UUID | None = None
    created: bool
    title: str
    company_name: str | None = None
    risk_level: str | None = None
    note: str = ""


class ExtractedField(BaseModel):
    id: str
    label: str = ""
    name: str = ""
    type: str = "text"
    autocomplete: str = ""
    required: bool = False
    options: list[str] = Field(default_factory=list)
    value: str = ""
    section: str = ""
    maxlength: int | None = None
    surrounding_text: str = ""


class PlanPageBody(BaseModel):
    fields: list[ExtractedField]
    page_url: str = ""
    page_text: str = ""
    platform: str = "generic"
    job_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    track_id: uuid.UUID | None = None
    profile_id: uuid.UUID
    run_id: uuid.UUID | None = None


class FillInstruction(BaseModel):
    field_id: str
    action: Literal["fill", "select", "skip", "checkpoint"] = "fill"
    value: str | None = None
    canonical_key: str | None = None
    source: str | None = None
    confidence: float = 0.0
    pii_class: Literal["public", "personal", "sensitive"] = "personal"
    checkpoint_kind: str | None = None
    note: str | None = None
    badge: str | None = None


class PlanPageResult(BaseModel):
    run_id: uuid.UUID
    platform: str
    autofill_allowed: bool
    instructions: list[FillInstruction]
    page_ai_restricted: bool = False
    resume_upload_url: str | None = None
    resume_file_name: str | None = None
    notes: list[str] = Field(default_factory=list)


class StartRunBody(BaseModel):
    profile_id: uuid.UUID
    platform: str = "generic"
    page_url: str = ""
    job_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    track_id: uuid.UUID | None = None


class StartRunResult(BaseModel):
    run_id: uuid.UUID
    status: str
    autofill_allowed: bool


class LogAppliedBody(BaseModel):
    track_job_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    track_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    notes: str = ""
    confirmation_url: str = ""


class AnswerInsertBody(BaseModel):
    profile_id: uuid.UUID
    question: str
    page_context: str = ""
    application_id: uuid.UUID | None = None


class AnswerInsertResult(BaseModel):
    draft: str
    ai_restricted: bool
    source: str
    note: str | None = None
