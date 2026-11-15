"""Source catalog + track_sources + country registry."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    adapter: Mapped[str] = mapped_column(String(64), nullable=False)
    terms_note: Mapped[str] = mapped_column(Text, server_default="")
    enabled_global: Mapped[bool] = mapped_column(Boolean, server_default="true")
    circuit_open: Mapped[bool] = mapped_column(Boolean, server_default="false")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    success_count: Mapped[int] = mapped_column(Integer, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, server_default="0")
    jobs_ingested: Mapped[int] = mapped_column(Integer, server_default="0")
    avg_latency_ms: Mapped[float | None] = mapped_column(Float)
    block_signals: Mapped[int] = mapped_column(Integer, server_default="0")
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TrackSource(Base):
    __tablename__ = "track_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE")
    )
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CountrySourceRegistry(Base):
    __tablename__ = "country_source_registry"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    country: Mapped[str] = mapped_column(String(8), nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    coverage: Mapped[str] = mapped_column(String(32), server_default="partial")
    note: Mapped[str] = mapped_column(Text, server_default="")


class SourceCoverage(Base):
    """Global honesty table for how well a source covers (industry, country)."""

    __tablename__ = "source_coverage"
    __table_args__ = (
        CheckConstraint(
            "coverage IN ('strong','partial','thin','none')", name="ck_source_coverage_level"
        ),
    )

    source_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    country: Mapped[str] = mapped_column(String(8), primary_key=True)
    industry: Mapped[str] = mapped_column(String(48), primary_key=True)
    coverage: Mapped[str] = mapped_column(String(16), server_default="thin")
    note: Mapped[str] = mapped_column(Text, server_default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SourceQueryCache(Base):
    """Shared cache for keyword + location search calls. Global, no tenant data."""

    __tablename__ = "source_query_cache"
    __table_args__ = (UniqueConstraint("source_key", "query_hash", name="uq_source_query_cache"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="[]")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
