"""Answer Desk API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ParseBody(BaseModel):
    text: str = Field(min_length=1, max_length=40_000)
    profile_id: uuid.UUID
    application_id: uuid.UUID | None = None
    page_context: str = Field(default="", max_length=8_000)


class ToneBody(BaseModel):
    tone: Literal["shorter", "more_specific", "more_casual", "more_formal"]


class ItemPatch(BaseModel):
    draft: str = Field(max_length=12_000)


class SaveBankBody(BaseModel):
    key: str = Field(default="custom_desk", min_length=2, max_length=80)
    approve: bool = True


class StanceBody(BaseModel):
    ai_use_stance: str = Field(max_length=2000)


class ItemRead(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    sort_order: int
    question: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    ai_restricted: bool = False
    legal_flag: bool = False
    source: str
    draft: str = ""
    fact_notes: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    banned_hits: list[str] = Field(default_factory=list)
    char_limit: int | None = None
    format: str = "text"
    answer_bank_id: uuid.UUID | None = None
    from_answer_bank: bool = False
    message: str = ""


class SessionRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    application_id: uuid.UUID | None = None
    page_restricted: bool = False
    created_at: datetime | None = None
    items: list[ItemRead] = Field(default_factory=list)


class RestrictionProbe(BaseModel):
    text: str = Field(min_length=1, max_length=8_000)
    page_context: str = ""


class RestrictionRead(BaseModel):
    restricted: bool
    page_level: bool
    matched: str = ""
    score: float = 0.0
