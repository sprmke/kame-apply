"""API schemas for agent bridge consent, tokens, routing, inbox."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConsentBody(BaseModel):
    pending_id: uuid.UUID
    workspace_id: uuid.UUID
    profile_id: uuid.UUID
    scopes: list[str] = Field(default_factory=list)


class ConsentResult(BaseModel):
    redirect_url: str


class PendingAuthRead(BaseModel):
    id: uuid.UUID
    client_id: str
    client_name: str
    scopes: list[str]
    redirect_uri: str
    expires_at: datetime


class TokenRead(BaseModel):
    id: uuid.UUID
    client_id: str
    client_name: str
    token_kind: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None


class PatCreate(BaseModel):
    profile_id: uuid.UUID
    scopes: list[str] = Field(default_factory=list)
    label: str = "personal-access-token"


class PatCreated(BaseModel):
    id: uuid.UUID
    token: str
    scopes: list[str]


class RoutingItem(BaseModel):
    feature: str
    route: str
    fallback: bool = False


class RoutingPut(BaseModel):
    feature: str
    route: str
    fallback: bool = False


class InboxStatus(BaseModel):
    waiting: int
    leased: int
    last_picked_up_at: str | None
    command: str


class AgentTaskCreate(BaseModel):
    profile_id: uuid.UUID
    kind: str
    input: dict = Field(default_factory=dict)
    priority: int = 0
    fallback_enabled: bool = False
