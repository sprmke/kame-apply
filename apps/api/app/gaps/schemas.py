from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class GapPlanItemRead(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    skill: str
    suggestion: str
    resource_url: str
    status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class GapStatusUpdate(BaseModel):
    status: str = Field(pattern="^(open|in_progress|done|skipped)$")
