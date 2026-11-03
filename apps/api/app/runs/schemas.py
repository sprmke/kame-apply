from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StartRunnerBody(BaseModel):
    application_id: uuid.UUID
    allow_submit: bool = False


class RunnerTokenCreate(BaseModel):
    label: str = Field(default="cloud", max_length=80)
    mode: Literal["cloud", "local"] = "cloud"


class RunnerTokenCreated(BaseModel):
    id: uuid.UUID
    token: str
    label: str
    mode: str


class RunnerTokenRead(BaseModel):
    id: uuid.UUID
    label: str
    mode: str
    last_seen_at: datetime | None
    created_at: datetime


class ApplyRunRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID | None
    job_id: uuid.UUID | None
    track_id: uuid.UUID | None
    profile_id: uuid.UUID
    status: str
    source: str
    ats: str
    page_url: str
    platform: str
    policy: dict[str, Any]
    submit_approved: bool
    failure_reason: str | None
    last_step_seq: int
    runner_id: str | None
    control_mode: str = "agent"
    live_mode: str = "off"
    controller_user_id: uuid.UUID | None = None
    user_edited_fields: list[Any] = Field(default_factory=list)
    live_telemetry: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None
    ended_at: datetime | None
    heartbeat_at: datetime | None
    created_at: datetime


class ApplyRunStepRead(BaseModel):
    id: uuid.UUID
    seq: int
    page_url: str
    action: str
    field_label: str
    value_redacted: str
    canonical_key: str | None
    source_fact_ref: str | None
    pii_class: str
    screenshot_r2: str | None
    screenshot_url: str | None = None
    outcome: str
    created_at: datetime


class CheckpointRead(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    kind: str
    detail: dict[str, Any]
    status: str
    decision: dict[str, Any] | None
    decided_at: datetime | None
    created_at: datetime


class CheckpointResolveBody(BaseModel):
    decision: Literal[
        "continue",
        "skip",
        "approve_submit",
        "deny_submit",
        "handoff_extension",
        "cancel",
        "typed_value",
    ]
    value: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=500)


class ClaimBody(BaseModel):
    runner_id: str = Field(min_length=1, max_length=120)


class HeartbeatBody(BaseModel):
    runner_id: str = Field(min_length=1, max_length=120)
    status: str | None = None
    page_url: str | None = None


class StepUploadBody(BaseModel):
    seq: int
    page_url: str = ""
    action: str = "fill"
    field_label: str = ""
    value_redacted: str = ""
    canonical_key: str | None = None
    source_fact_ref: str | None = None
    pii_class: str = "personal"
    screenshot_r2: str | None = None
    # Blurred PNG bytes, base64. Stored under ws/<workspace>/runs/<run>/step-<seq>.png.
    screenshot_b64: str | None = None
    outcome: str = "ok"


class CheckpointCreateBody(BaseModel):
    kind: str
    detail: dict[str, Any] = Field(default_factory=dict)


class HandoffRead(BaseModel):
    url: str
    run_id: uuid.UUID
    last_step_seq: int
    open_checkpoint_id: uuid.UUID | None = None


class OkRead(BaseModel):
    ok: bool = True


class LiveTokenRead(BaseModel):
    token: str
    role: str
    ws_path: str
    expires_at: datetime
    run_id: uuid.UUID


class LiveStateRead(BaseModel):
    run_id: uuid.UUID
    control_mode: str
    live_mode: str
    controller_user_id: uuid.UUID | None
    viewers: int
    user_edited_fields: list[Any]
    telemetry: dict[str, Any]


class LiveModeBody(BaseModel):
    live_mode: Literal["screencast", "screenshot", "off"]


class LiveFieldLockBody(BaseModel):
    field_id: str
    label: str = ""
