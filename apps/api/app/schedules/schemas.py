"""Schedule + run-history API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Scope = Literal["all", "source"]
Preset = Literal[
    "hourly",
    "every_2_hours",
    "every_4_hours",
    "daily_morning",
    "weekdays_2h",
    "custom",
]


class QuietHours(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Scope = "all"
    source_id: uuid.UUID | None = None
    preset: Preset = "every_2_hours"
    cron: str | None = None
    timezone: str = "UTC"
    quiet_hours: QuietHours | None = None
    daily_cap: int = Field(default=12, ge=0, le=48)
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Scope | None = None
    source_id: uuid.UUID | None = None
    preset: Preset | None = None
    cron: str | None = None
    timezone: str | None = None
    quiet_hours: QuietHours | None = None
    daily_cap: int | None = Field(default=None, ge=0, le=48)
    enabled: bool | None = None


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    track_id: uuid.UUID
    scope: str
    source_id: uuid.UUID | None
    preset: str
    cron: str
    timezone: str
    quiet_hours: dict[str, Any]
    daily_cap: int
    enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_skip_reason: str
    preview: str
    created_at: datetime
    updated_at: datetime


class TickBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    now: datetime | None = None
    workspace_only: bool = True


class TickResult(BaseModel):
    fired: int
    skipped: int
    digests: int
    details: list[dict[str, Any]]


class DiscoveryRunHistoryRead(BaseModel):
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
    duration_ms: int | None = None
