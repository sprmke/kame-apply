from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(default="", max_length=320)
    company: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=200)
    linkedin_url: str = Field(default="", max_length=500)
    source: str = Field(default="csv", max_length=32)


class ContactRead(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    company: str
    title: str
    linkedin_url: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactImportBody(BaseModel):
    contacts: list[ContactCreate] = Field(min_length=1, max_length=500)


class ContactImportResult(BaseModel):
    imported: int


class MatchRead(BaseModel):
    contact: ContactRead
    score: float
    reason: str


class ReferralDraftRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    contact_id: uuid.UUID | None
    draft: str
    created_at: datetime
    contact_name: str = ""

    model_config = {"from_attributes": True}


class DraftCreateBody(BaseModel):
    contact_id: uuid.UUID
