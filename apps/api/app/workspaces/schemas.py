import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

AssignableRole = Literal["admin", "member", "viewer"]


def _clean_name(v: str) -> str:
    v = v.strip()
    if not v or any(ord(ch) < 32 or ord(ch) == 127 for ch in v):
        raise ValueError("name must be plain text")  # also keeps mail subjects header-safe
    return v


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    _clean = field_validator("name")(_clean_name)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    _clean = field_validator("name")(_clean_name)


class WorkspaceRead(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    role: str


class MemberRead(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str | None
    role: str
    joined_at: datetime


class MemberUpdate(BaseModel):
    role: AssignableRole


class TransferIn(BaseModel):
    user_id: uuid.UUID


class InvitationCreate(BaseModel):
    email: EmailStr
    role: AssignableRole = "member"


class InvitationRead(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    created_at: datetime


class InviteAcceptIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class OkRead(BaseModel):
    ok: bool = True


class LimitsRead(BaseModel):
    max_members: int
    max_ai_credentials: int
    max_tracks: int
    max_sources: int
    max_storage_mb: int
    max_ai_budget_cents: int
    members_used: int
