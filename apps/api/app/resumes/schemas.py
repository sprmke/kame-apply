"""Resume Studio API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResumeVersionRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    track_id: uuid.UUID | None = None
    kind: str
    label: str
    template: str
    page_size: str
    content: dict[str, Any]
    critique: dict[str, Any] = Field(default_factory=dict)
    parse_gate: dict[str, Any] = Field(default_factory=dict)
    r2_pdf: str | None = None
    r2_docx: str | None = None
    r2_txt: str | None = None
    accepted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ResumeCreateBody(BaseModel):
    profile_id: uuid.UUID
    track_id: uuid.UUID | None = None
    label: str = ""
    template: str = "classic"
    page_size: Literal["letter", "a4"] = "letter"


class CritiqueRead(BaseModel):
    categories: dict[str, Any]
    top_fixes: list[Any] = Field(default_factory=list)
    findings: list[Any] = Field(default_factory=list)
    skim_zone: dict[str, Any] = Field(default_factory=dict)


class ImproveBody(BaseModel):
    window_days: int = Field(default=30, ge=7, le=180)


class ChangeRead(BaseModel):
    id: uuid.UUID
    path: str
    op: str
    before: str
    after: str
    reason: str
    evidence_refs: list[uuid.UUID] = Field(default_factory=list)
    status: str
    ask: str | None = None


class ChangeDecisionBody(BaseModel):
    status: Literal["accepted", "rejected"]


class BulkChangesBody(BaseModel):
    status: Literal["accepted", "rejected"]
    change_ids: list[uuid.UUID] | None = None  # None = all proposed


class RenderBody(BaseModel):
    template: str | None = None
    page_size: Literal["letter", "a4"] | None = None
    broken: bool = False  # dev/test: force parse-gate failure


class RenderRead(BaseModel):
    parse_gate: dict[str, Any]
    pdf_url: str | None = None
    docx_url: str | None = None
    txt_url: str | None = None
    engine: str
    filename_base: str


class InsightsRead(BaseModel):
    track_id: uuid.UUID
    window_days: int
    sample_size: int
    low_confidence: bool
    skills: list[Any] = Field(default_factory=list)
    titles: list[Any] = Field(default_factory=list)
    salary: dict[str, Any] = Field(default_factory=dict)
    years_required: dict[str, Any] = Field(default_factory=dict)
    certifications: list[Any] = Field(default_factory=list)
    comparison: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime | None = None


class ParseViewRead(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    sections: list[str] = Field(default_factory=list)
    employers: list[Any] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class OkRead(BaseModel):
    ok: bool = True
