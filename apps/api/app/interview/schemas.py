from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class InterviewPrepRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    company_brief: str
    likely_questions: list[Any]
    star_stories: list[Any]
    checklist: list[Any]
    citations: list[Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
