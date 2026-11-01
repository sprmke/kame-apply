from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class InterviewPrep(Base):
    __tablename__ = "interview_preps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    company_brief: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    likely_questions: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)
    star_stories: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)
    checklist: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)
    citations: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
