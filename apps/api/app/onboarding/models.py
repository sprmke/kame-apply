"""Setup draft storage: one row per resume reading that fills the pages about a person.

The bundle holds personal data copied from a resume, the same class as `documents.parsed`.
It is never logged. Rows are workspace-scoped and RLS-forced like every tenant table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

OPEN_STATUSES = ("queued", "running", "ready", "applying")
FINAL_STATUSES = ("applied", "failed", "cancelled", "discarded", "expired", "reverted")


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class SetupDraft(Base):
    __tablename__ = "setup_drafts"

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    subject: Mapped[str] = mapped_column(String(16), server_default="self")
    mode: Mapped[str] = mapped_column(String(16), server_default="new")
    status: Mapped[str] = mapped_column(String(16), server_default="queued")
    role_text: Mapped[str | None] = mapped_column(Text)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    steps: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    bundle: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    decisions: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    base: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    apply_key: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(64))
    ai_cost_micros: Mapped[int] = mapped_column(BigInteger, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "uq_setup_drafts_open_profile",
            "profile_id",
            unique=True,
            postgresql_where=text("status IN ('queued','running','ready','applying')"),
        ),
        Index("ix_setup_drafts_workspace_created", "workspace_id", text("created_at DESC")),
    )
