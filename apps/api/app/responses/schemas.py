from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class IngestReplyBody(BaseModel):
    application_id: uuid.UUID | None = None
    sender: str = Field(default="", max_length=500)
    subject: str = Field(default="", max_length=500)
    body_text: str = Field(default="", max_length=50_000)


class ResponseMessageRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID | None
    sender: str
    subject: str
    body_text: str
    classification: str
    confidence: float
    scam_level: str
    scam_reasons: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusProposalRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    response_message_id: uuid.UUID | None
    from_status: str
    to_status: str
    reason: str
    citation: str
    status: str
    created_at: datetime
    decided_at: datetime | None
    company_name: str = ""
    job_title: str = ""

    model_config = {"from_attributes": True}


class DecideProposalBody(BaseModel):
    accept: bool
    note: str = Field(default="", max_length=500)


class BatchDecideBody(BaseModel):
    proposal_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    accept: bool
    note: str = Field(default="", max_length=500)
