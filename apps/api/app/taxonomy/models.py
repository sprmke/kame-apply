"""Global taxonomy tables. No workspace_id; shared read-only corpus for all tenants.

Embedding columns (vector(384)) exist in Postgres for refresh jobs; they are not mapped
here so the API stays free of a hard pgvector Python dependency on the request path.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
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


class TaxonomyOccupation(Base):
    __tablename__ = "taxonomy_occupations"
    __table_args__ = (
        UniqueConstraint("scheme", "code", name="uq_taxonomy_occupations_scheme_code"),
    )

    id: Mapped[uuid.UUID] = _pk()
    scheme: Mapped[str] = mapped_column(String(16))  # esco | onet | isco | soc
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    isco_code: Mapped[str | None] = mapped_column(String(16))
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    alt_titles: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaxonomySkill(Base):
    __tablename__ = "taxonomy_skills"
    __table_args__ = (UniqueConstraint("scheme", "code", name="uq_taxonomy_skills_scheme_code"),)

    id: Mapped[uuid.UUID] = _pk()
    scheme: Mapped[str] = mapped_column(String(16))  # esco | onet
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(300))
    skill_type: Mapped[str | None] = mapped_column(String(32))
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    aliases: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaxonomyOccupationSkill(Base):
    __tablename__ = "taxonomy_occupation_skills"
    __table_args__ = (
        UniqueConstraint("occupation_id", "skill_id", "relation", name="uq_taxonomy_occ_skill_rel"),
    )

    id: Mapped[uuid.UUID] = _pk()
    occupation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_occupations.id", ondelete="CASCADE")
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_skills.id", ondelete="CASCADE")
    )
    relation: Mapped[str] = mapped_column(String(24), server_default="essential")


class TaxonomyCrosswalk(Base):
    __tablename__ = "taxonomy_crosswalks"
    __table_args__ = (
        UniqueConstraint(
            "from_scheme",
            "from_code",
            "to_scheme",
            "to_code",
            name="uq_taxonomy_crosswalk",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    from_scheme: Mapped[str] = mapped_column(String(16))
    from_code: Mapped[str] = mapped_column(String(64))
    to_scheme: Mapped[str] = mapped_column(String(16))
    to_code: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[str] = mapped_column(String(16), server_default="exact")


class TaxonomyAlias(Base):
    """Extra aliases for skills/titles (JS → JavaScript, K8s → Kubernetes)."""

    __tablename__ = "taxonomy_aliases"
    __table_args__ = (UniqueConstraint("kind", "alias_key", name="uq_taxonomy_aliases_kind_key"),)

    id: Mapped[uuid.UUID] = _pk()
    kind: Mapped[str] = mapped_column(String(16))  # skill | title
    alias: Mapped[str] = mapped_column(String(200))
    alias_key: Mapped[str] = mapped_column(String(200))
    canonical: Mapped[str] = mapped_column(String(300))
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_skills.id", ondelete="SET NULL")
    )
    occupation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_occupations.id", ondelete="SET NULL")
    )


class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id: Mapped[uuid.UUID] = _pk()
    as_of: Mapped[str] = mapped_column(String(10))
    base: Mapped[str] = mapped_column(String(3), server_default="USD")
    rates: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    source: Mapped[str] = mapped_column(String(32), server_default="fallback")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrackTemplate(Base):
    """Curated starter Tracks (global, not tenant-owned)."""

    __tablename__ = "track_templates"
    __table_args__ = (Index("ix_track_templates_industry", "industry"),)

    id: Mapped[uuid.UUID] = _pk()
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, server_default="")
    icon: Mapped[str] = mapped_column(String(64), server_default="ph:path")
    color_hue: Mapped[int] = mapped_column(Integer, server_default="1")
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    nl_seed: Mapped[str] = mapped_column(Text, server_default="")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
