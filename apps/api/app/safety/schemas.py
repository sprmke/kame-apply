"""Safety API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RiskReasonRead(BaseModel):
    signal: str
    layer: str | None = None
    weight: int | float | None = None
    evidence: str = ""


class JobRiskRead(BaseModel):
    job_id: uuid.UUID
    level: Literal["green", "yellow", "red"]
    score: float
    reasons: list[Any] = Field(default_factory=list)
    layers: dict[str, Any] = Field(default_factory=dict)
    model_version: str
    partial: bool = False
    assessed_at: datetime | None = None
    override: str | None = None


class RiskDecisionBody(BaseModel):
    decision: Literal["continue", "skip", "reported", "not_scam"]
    note: str = Field(default="", max_length=500)
    confirm_risk: bool = False  # required when decision=continue and level=red


class MidRunSignalBody(BaseModel):
    job_id: uuid.UUID
    signals: list[dict[str, Any]] = Field(default_factory=list)


class CheckThisBody(BaseModel):
    text: str | None = Field(default=None, max_length=20_000)
    url: str | None = Field(default=None, max_length=2000)


class CheckThisRead(BaseModel):
    level: Literal["green", "yellow", "red"]
    score: float
    reasons: list[Any] = Field(default_factory=list)
    advice: str = ""
    kind: str = "message"


class FieldClassifyBody(BaseModel):
    label: str | None = None
    name: str | None = None
    autocomplete: str | None = None
    input_type: str | None = None
    pattern: str | None = None
    country: str | None = None


class FieldClassifyRead(BaseModel):
    classification: Literal["public", "personal", "sensitive"]
    reason: str
    checkpoint: bool


class FlaggedJobRead(BaseModel):
    job_id: uuid.UUID
    track_job_id: uuid.UUID | None = None
    title: str
    company_name: str | None = None
    level: str
    score: float
    reasons: list[Any] = Field(default_factory=list)
    override: str | None = None


class OkRead(BaseModel):
    ok: bool = True


class AssessResultRead(BaseModel):
    job_id: uuid.UUID
    level: str
    score: float
    partial: bool = False
