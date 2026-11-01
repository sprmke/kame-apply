"""Notification API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Channel = Literal["in_app", "email", "push", "telegram"]
Event = Literal[
    "strong_match",
    "needs_review",
    "risk_flag",
    "run_failed",
    "budget_reached",
    "digest",
]

EVENTS: tuple[str, ...] = (
    "strong_match",
    "needs_review",
    "risk_flag",
    "run_failed",
    "budget_reached",
    "digest",
)
CHANNELS: tuple[str, ...] = ("in_app", "email", "push", "telegram")


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    body: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class PrefCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Channel
    event: Event
    enabled: bool


class PrefsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cells: list[PrefCell] = Field(min_length=1)


class PrefsMatrix(BaseModel):
    cells: list[PrefCell]


class NeedsYouItem(BaseModel):
    kind: str
    title: str
    detail: str
    href: str
    created_at: datetime | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class NeedsYouRead(BaseModel):
    count: int
    items: list[NeedsYouItem]
