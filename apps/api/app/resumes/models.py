"""Resume Studio ORM."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="SET NULL")
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(16), server_default="base")
    label: Mapped[str] = mapped_column(String(200), server_default="")
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    template: Mapped[str] = mapped_column(String(64), server_default="classic")
    page_size: Mapped[str] = mapped_column(String(16), server_default="letter")
    r2_pdf: Mapped[str | None] = mapped_column(String(500))
    r2_docx: Mapped[str | None] = mapped_column(String(500))
    r2_txt: Mapped[str | None] = mapped_column(String(500))
    critique: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    lens_report: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    parse_gate: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="SET NULL")
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResumeChange(Base):
    __tablename__ = "resume_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(300), nullable=False)
    op: Mapped[str] = mapped_column(String(32), server_default="rewrite")
    before: Mapped[str] = mapped_column(Text, server_default="")
    after: Mapped[str] = mapped_column(Text, server_default="")
    reason: Mapped[str] = mapped_column(Text, server_default="")
    evidence_refs: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), server_default="{}"
    )
    status: Mapped[str] = mapped_column(String(16), server_default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketInsight(Base):
    __tablename__ = "market_insights"
    __table_args__ = (
        UniqueConstraint("track_id", "window_days", name="uq_market_insights_track_window"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    window_days: Mapped[int] = mapped_column(Integer, server_default="30")
    sample_size: Mapped[int] = mapped_column(Integer, server_default="0")
    skills: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    titles: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    salary: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    years_required: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    certifications: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    comparison: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    secondary_research: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    low_confidence: Mapped[bool] = mapped_column(Boolean, server_default="false")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
