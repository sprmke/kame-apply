"""API schemas for sources, discovery, boards."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceHealthRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    name: str
    kind: str
    enabled_global: bool
    circuit_open: bool
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error: str | None
    success_count: int
    error_count: int
    jobs_ingested: int
    avg_latency_ms: float | None
    block_signals: int
    terms_note: str


class TrackSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    source_key: str
    enabled: bool
    params: dict[str, Any]


class TrackSourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    params: dict[str, Any] | None = None


class DiscoveryRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    track_id: uuid.UUID
    status: str
    trigger: str
    progress: dict[str, Any]
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class AddCareersIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=8, max_length=500)


class CompanyBoardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    ats: str
    slug: str
    url: str
    status: str
    poll_tier: str
    validated_at: datetime | None
    validation_method: str


class TrackJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    track_id: uuid.UUID
    job_id: uuid.UUID
    score: float | None
    status: str
    title: str | None = None
    company_name: str | None = None
    apply_url: str | None = None
    work_mode: str | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company_id: uuid.UUID | None
    apply_url: str
    canonical_url: str
    status: str
    work_mode: str | None
    locations: list[Any]
    salary: dict[str, Any]
    posted_at: datetime | None


class OkRead(BaseModel):
    ok: bool = True


class DirectoryStatsRead(BaseModel):
    boards_active: int
    boards_candidate: int = 0
    companies: int
    sources: int
