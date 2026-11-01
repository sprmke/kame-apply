"""Tenant Track + criteria rows, plus shared geocode cache."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        Index("ix_tracks_workspace_status_sort", "workspace_id", "status", "sort_order"),
    )

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str] = mapped_column(String(64), server_default="ph:path")
    color_hue: Mapped[int] = mapped_column(Integer, server_default="1")
    status: Mapped[str] = mapped_column(String(16), server_default="active")  # active|archived
    autonomy: Mapped[str] = mapped_column(String(16), server_default="discover")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    summary: Mapped[str] = mapped_column(Text, server_default="")
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    template_slug: Mapped[str | None] = mapped_column(String(80))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TrackCriteria(Base):
    __tablename__ = "track_criteria"
    __table_args__ = (UniqueConstraint("track_id", name="uq_track_criteria_track_id"),)

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE")
    )
    nl_text: Mapped[str] = mapped_column(Text, server_default="")
    structured: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    compiled: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GeocodeCache(Base):
    """Shared Nominatim cache (global)."""

    __tablename__ = "geocode_cache"
    __table_args__ = (UniqueConstraint("query_key", name="uq_geocode_cache_query_key"),)

    id: Mapped[uuid.UUID] = _pk()
    query_key: Mapped[str] = mapped_column(String(300))
    query: Mapped[str] = mapped_column(String(300))
    lat: Mapped[Any] = mapped_column(Numeric(9, 6))
    lon: Mapped[Any] = mapped_column(Numeric(9, 6))
    country: Mapped[str | None] = mapped_column(String(2))
    display_name: Mapped[str] = mapped_column(Text)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
