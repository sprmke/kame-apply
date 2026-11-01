from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PolicyReason(BaseModel):
    code: str
    ok: bool
    detail: str


class PolicyVerdict(BaseModel):
    allow_submit: bool
    dry_run: bool
    reasons: list[PolicyReason]
    summary: str


class AutoSubmitSettingsRead(BaseModel):
    track_id: uuid.UUID
    autonomy: str
    live_enabled: bool
    dry_run_remaining: int
    score_threshold: float
    kill_switch: bool
    workspace_kill_switch: bool
    global_enabled: bool


class AutoSubmitSettingsUpdate(BaseModel):
    live_enabled: bool | None = None
    dry_run_remaining: int | None = Field(default=None, ge=0, le=100)
    score_threshold: float | None = Field(default=None, ge=0, le=100)
    kill_switch: bool | None = None


class WorkspaceKillSwitchBody(BaseModel):
    enabled: bool  # True = kill (block auto-submit)


class DryRunReportRead(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    application_id: uuid.UUID
    run_id: uuid.UUID | None
    would_submit: bool
    reasons: list[dict[str, Any]]
    created_at: datetime


class BatchApproveBody(BaseModel):
    answer_bank_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    approved: bool = True


class BatchApproveRead(BaseModel):
    updated: int


class AnomalyStatusRead(BaseModel):
    paused: bool
    reason: str | None = None
    failure_rate_24h: float | None = None
    sample_size: int = 0


class ExplainRead(BaseModel):
    application_id: uuid.UUID
    verdict: PolicyVerdict
    mode: Literal["assist", "dry_run", "live", "blocked"]
