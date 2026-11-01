"""Tailor + applications API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AppStatus = Literal[
    "draft",
    "ready",
    "in_progress",
    "needs_you",
    "submitted",
    "responded",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "ghosted",
    "job_closed",
]


class TailorStartBody(BaseModel):
    include_cover_letter: bool = True
    base_version_id: uuid.UUID | None = None


class TailorRunRead(BaseModel):
    id: uuid.UUID
    track_job_id: uuid.UUID
    job_id: uuid.UUID
    track_id: uuid.UUID
    profile_id: uuid.UUID
    status: str
    base_version_id: uuid.UUID | None = None
    draft_version_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    lens_before: dict[str, Any] = Field(default_factory=dict)
    lens_after: dict[str, Any] = Field(default_factory=dict)
    gaps: list[Any] = Field(default_factory=list)
    knockouts: list[Any] = Field(default_factory=list)
    proposed_changes: list[Any] = Field(default_factory=list)
    progress: dict[str, Any] = Field(default_factory=dict)
    cover_letter: dict[str, Any] | None = None
    draft_content: dict[str, Any] | None = None
    error: str = ""
    created_at: datetime | None = None


class TailorAcceptBody(BaseModel):
    include_cover_letter: bool = True
    method: Literal["manual", "extension", "runner", "answer_desk"] = "manual"


class ApplicationRead(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    job_id: uuid.UUID
    track_job_id: uuid.UUID | None = None
    profile_id: uuid.UUID
    status: str
    method: str
    resume_version_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    job_snapshot_r2: str | None = None
    lens_before: dict[str, Any] = Field(default_factory=dict)
    lens_after: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    company_name: str = ""
    job_title: str = ""
    apply_url: str = ""
    follow_up_draft: str = ""
    reminder_days: int = 7
    reminder_at: datetime | None = None
    responded_at: datetime | None = None
    interview_at: datetime | None = None
    outcome_at: datetime | None = None
    ghosted_suggested_at: datetime | None = None
    tailored: bool = False
    lens_grade: str = ""
    source_key: str = ""
    created_at: datetime | None = None
    submitted_at: datetime | None = None
    updated_at: datetime | None = None
    duplicate_warning: bool = False
    events: list[dict[str, Any]] = Field(default_factory=list)
    reminders: list[dict[str, Any]] = Field(default_factory=list)
    job: dict[str, Any] | None = None


class ApplicationListRead(BaseModel):
    total: int
    items: list[ApplicationRead]
    limit: int
    offset: int


class ApplicationStatusBody(BaseModel):
    status: AppStatus
    note: str = ""


class ApplicationNotesBody(BaseModel):
    notes: str = Field(max_length=8000)


class MarkAppliedBody(BaseModel):
    track_job_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    track_id: uuid.UUID | None = None
    method: Literal["manual", "extension", "runner", "answer_desk"] = "manual"
    notes: str = ""


class ManualCreateBody(BaseModel):
    track_id: uuid.UUID
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(default="", max_length=500)
    method: Literal["manual", "extension", "runner", "answer_desk"] = "manual"
    notes: str = ""
    mark_submitted: bool = True


class SavedViewBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    filters: dict[str, Any] = Field(default_factory=dict)


class CoverLetterRead(BaseModel):
    id: uuid.UUID
    content: str
    word_count: int
    company_reason: str
    status: str
    evidence_refs: list[uuid.UUID] = Field(default_factory=list)
