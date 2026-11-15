"""API schemas for Tracks and criteria."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.tracks.criteria import CriteriaV1

Autonomy = Literal["discover", "prepare", "assist", "auto_submit"]
TrackStatus = Literal["active", "paused", "archived"]


class TrackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=200)
    icon: str = Field(default="ph:path", max_length=64)
    color_hue: int = Field(default=1, ge=1, le=8)
    autonomy: Autonomy = "prepare"
    nl_text: str = Field(default="", max_length=8000)
    criteria: CriteriaV1 | None = None
    template_slug: str | None = Field(default=None, max_length=80)
    # Build a full role-based search setup from nl_text (falls back to deterministic defaults).
    suggest: bool = False
    industry: str | None = Field(default=None, max_length=48)


class TrackUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    icon: str | None = Field(default=None, max_length=64)
    color_hue: int | None = Field(default=None, ge=1, le=8)
    autonomy: Autonomy | None = None
    settings: dict[str, Any] | None = None
    industry: str | None = Field(default=None, max_length=48)


class TrackReorder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordered_ids: list[uuid.UUID] = Field(min_length=1)


class CriteriaPut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criteria: CriteriaV1
    nl_text: str | None = Field(default=None, max_length=8000)


class CriteriaCompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=8000)
    apply: bool = False


class CriteriaCompilePreview(BaseModel):
    criteria: CriteriaV1
    summary: str
    diff: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    invented_fields: list[str] = Field(default_factory=list)


class CriteriaPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=8000)


class CriteriaPlanPreview(BaseModel):
    criteria: CriteriaV1
    summary: str
    diff: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    source: Literal["ai", "defaults"] = "defaults"
    ai_error: str | None = None
    name: str = ""
    applied: bool = False


class CriteriaSuggestRequest(CriteriaPlanRequest):
    apply: bool = False


class TrackCriteriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nl_text: str
    structured: dict[str, Any]
    compiled: dict[str, Any]
    version: int
    summary: str
    warnings: list[dict[str, Any]] = Field(default_factory=list)


class TrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    profile_id: uuid.UUID
    name: str
    icon: str
    color_hue: int
    status: TrackStatus
    autonomy: Autonomy
    sort_order: int
    summary: str
    settings: dict[str, Any]
    template_slug: str | None
    industry: str
    industry_version: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    preview_message: str = "Preview available after first discovery"


class TrackDetail(TrackRead):
    criteria: TrackCriteriaRead


class TrackTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    industry: str
    description: str
    icon: str
    color_hue: int
    nl_seed: str
    criteria: dict[str, Any]


class OkRead(BaseModel):
    ok: bool = True


class GeocodeRead(BaseModel):
    place: str
    lat: float
    lon: float
    country: str | None
    display_name: str
    cached: bool


class RecommendedSettingsRead(BaseModel):
    autonomy: Autonomy
    preset: str
    timezone: str
    quiet_hours: dict[str, Any]
    daily_cap: int
    minimum_match: int
    sources: int
    new_per_day: float
    per_run: int
    reasons: list[str]
