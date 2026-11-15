"""Workspace fields of work. Per-search industry lives on `tracks.industry`."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WorkspaceIndustry(Base):
    """One field of work for a workspace. `is_primary` drives defaults; extras allow two fields."""

    __tablename__ = "workspace_industries"
    __table_args__ = (
        Index(
            "uq_workspace_industries_primary",
            "workspace_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    industry_key: Mapped[str] = mapped_column(String(48), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # Accepted AI-drafted pack for "Something else". Never used to weaken safety or field types.
    custom_pack: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
