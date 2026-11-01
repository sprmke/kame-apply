from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class InboundAddressRead(BaseModel):
    id: uuid.UUID
    address: str
    enabled: bool
    created_at: datetime
    rotated_at: datetime | None


class InboundMessageRead(BaseModel):
    id: uuid.UUID
    sender: str
    subject: str
    provider: str
    status: str
    confidence: float
    jobs_created: int
    parsed: list[dict[str, Any]]
    created_at: datetime


class SetupGuideRead(BaseModel):
    provider: str
    title: str
    steps: list[str]


class PushSubscribeBody(BaseModel):
    endpoint: str = Field(min_length=8, max_length=2000)
    p256dh: str = Field(min_length=8, max_length=500)
    auth: str = Field(min_length=8, max_length=200)
    user_agent: str = Field(default="", max_length=300)


class PushSubscriptionRead(BaseModel):
    id: uuid.UUID
    endpoint: str
    created_at: datetime


class VapidPublicRead(BaseModel):
    public_key: str
    enabled: bool


class TelegramLinkRead(BaseModel):
    linked: bool
    chat_id: str | None = None
    link_code: str | None = None
    code_expires_at: datetime | None = None
    bot_username: str | None = None


class TelegramStartBody(BaseModel):
    pass


class OkRead(BaseModel):
    ok: bool = True


class WebhookAck(BaseModel):
    ok: bool = True
    message_id: uuid.UUID | None = None
    status: str = "received"
    jobs_created: int = 0


class ProviderGuide(BaseModel):
    provider: Literal[
        "linkedin",
        "indeed",
        "jobstreet",
        "glassdoor",
        "kalibrr",
        "google_alerts",
        "gmail",
        "outlook",
    ]
