import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
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


def _workspace() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))


def _profile() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )


def _stamp() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _workspace()
    display_name: Mapped[str] = mapped_column(String(200))
    headline: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))
    timezone: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16), server_default="en")
    work_authorization: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    salary_prefs: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    links: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    minimization: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = _stamp()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class _Section:
    """Columns every fact section shares."""

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _workspace()
    profile_id: Mapped[uuid.UUID] = _profile()
    do_not_use: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    confidential: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    source: Mapped[str] = mapped_column(String(12), server_default="user")
    created_at: Mapped[datetime] = _stamp()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Experience(_Section, Base):
    __tablename__ = "profile_experiences"

    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    employment_type: Mapped[str | None] = mapped_column(String(24))
    location: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    description: Mapped[str | None] = mapped_column(Text)


class Project(_Section, Base):
    __tablename__ = "profile_projects"

    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


class Bullet(_Section, Base):
    __tablename__ = "profile_bullets"

    experience_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profile_experiences.id", ondelete="CASCADE")
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profile_projects.id", ondelete="CASCADE")
    )
    text: Mapped[str] = mapped_column(Text)
    metrics: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    skills: Mapped[list[str]] = mapped_column(ARRAY(String(80)), server_default="{}")
    evidence_strength: Mapped[str] = mapped_column(String(8), server_default="weak")


class Education(_Section, Base):
    __tablename__ = "profile_education"

    institution: Mapped[str] = mapped_column(String(200))
    degree: Mapped[str | None] = mapped_column(String(200))
    field: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class Certification(_Section, Base):
    __tablename__ = "profile_certifications"

    name: Mapped[str] = mapped_column(String(200))
    issuer: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(12), server_default="certification")
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    jurisdiction: Mapped[str | None] = mapped_column(String(120))


class Language(_Section, Base):
    __tablename__ = "profile_languages"

    name: Mapped[str] = mapped_column(String(80))
    proficiency: Mapped[str | None] = mapped_column(String(16))


class Skill(_Section, Base):
    __tablename__ = "profile_skills"

    name: Mapped[str] = mapped_column(String(120))
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_skills.id", ondelete="SET NULL")
    )
    level: Mapped[str | None] = mapped_column(String(16))
    years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    last_used: Mapped[int | None] = mapped_column(Integer)
    evidence_refs: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), server_default="{}"
    )


class ProfileProposal(Base):
    """Interview draft. Applied to facts only after the user accepts."""

    __tablename__ = "profile_proposals"

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _workspace()
    profile_id: Mapped[uuid.UUID] = _profile()
    kind: Mapped[str] = mapped_column(String(32))
    target_type: Mapped[str] = mapped_column(String(24))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    question: Mapped[str] = mapped_column(Text)
    user_answer: Mapped[str] = mapped_column(Text, server_default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = _stamp()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VoiceProfile(Base):
    """Writing voice derived from pasted samples. Sample text is never written to activity_log."""

    __tablename__ = "voice_profiles"

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _workspace()
    profile_id: Mapped[uuid.UUID] = _profile()
    samples: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    style: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    banned_phrases: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    ai_use_stance: Mapped[str] = mapped_column(Text, server_default="")
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = _stamp()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnswerBank(Base):
    """Reusable form answers. Text is never logged; audit stores key/scope/approved only."""

    __tablename__ = "answer_bank"

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _workspace()
    profile_id: Mapped[uuid.UUID] = _profile()
    key: Mapped[str] = mapped_column(String(80))
    country: Mapped[str | None] = mapped_column(String(2))
    question_variants: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    answer: Mapped[str] = mapped_column(Text, server_default="")
    answer_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    scope: Mapped[str] = mapped_column(String(12), server_default="global")
    track_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = _stamp()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Document(Base):
    """Uploaded resume or related blob. Bytes live in R2 under `r2_key`; Postgres holds metadata
    and cleaned extracted text for the parse step."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = _pk()
    workspace_id: Mapped[uuid.UUID] = _workspace()
    profile_id: Mapped[uuid.UUID] = _profile()
    kind: Mapped[str] = mapped_column(String(24), server_default="resume_upload")
    r2_key: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(260))
    mime: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    ocr_used: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    warnings: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    extracted_text: Mapped[str | None] = mapped_column(Text)
    parsed: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    parse_quality: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = _stamp()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
