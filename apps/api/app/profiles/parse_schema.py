"""LLM output contract for resume → Career Profile drafts (Phase 3 slice 3).

Draft only: nothing enters profile tables until the user confirms (truthful-content, P1).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

LOW_CONFIDENCE = 0.6


class ConfidentText(BaseModel):
    value: str | None = Field(default=None, max_length=5000)
    confidence: float = Field(default=0.5, ge=0, le=1)
    span: str | None = Field(default=None, max_length=200)

    @field_validator("value", "span", mode="before")
    @classmethod
    def _blank_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class BulletDraft(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    metrics: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=30)
    confidence: float = Field(default=0.5, ge=0, le=1)
    span: str | None = Field(default=None, max_length=200)


class ExperienceDraft(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    employment_type: str | None = Field(default=None, max_length=24)
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=5000)
    bullets: list[BulletDraft] = Field(default_factory=list, max_length=40)
    confidence: float = Field(default=0.5, ge=0, le=1)
    span: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = None
        if self.is_current:
            self.end_date = None
        return self


class ProjectDraft(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    start_date: date | None = None
    end_date: date | None = None
    bullets: list[BulletDraft] = Field(default_factory=list, max_length=40)
    confidence: float = Field(default=0.5, ge=0, le=1)
    span: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = None
        return self


class EducationDraft(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    degree: str | None = Field(default=None, max_length=200)
    field: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    confidence: float = Field(default=0.5, ge=0, le=1)
    span: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = None
        return self


class CertificationDraft(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    kind: Literal["certification", "license"] = "certification"
    issued_on: date | None = None
    expires_on: date | None = None
    jurisdiction: str | None = Field(default=None, max_length=120)
    confidence: float = Field(default=0.5, ge=0, le=1)
    span: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _dates(self) -> Self:
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            self.expires_on = None
        return self


class LanguageDraft(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    proficiency: str | None = Field(default=None, max_length=16)
    confidence: float = Field(default=0.5, ge=0, le=1)
    span: str | None = Field(default=None, max_length=200)


class SkillDraft(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: str | None = Field(default=None, max_length=16)
    years: Decimal | None = Field(default=None, ge=0, le=80)
    last_used: int | None = Field(default=None, ge=1950, le=2100)
    confidence: float = Field(default=0.5, ge=0, le=1)
    span: str | None = Field(default=None, max_length=200)


class LinkDraft(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=0.5, ge=0, le=1)


class ProfileExtract(BaseModel):
    """Strict draft written to `documents.parsed` until the user confirms."""

    display_name: ConfidentText = Field(default_factory=ConfidentText)
    headline: ConfidentText = Field(default_factory=ConfidentText)
    summary: ConfidentText = Field(default_factory=ConfidentText)
    location: ConfidentText = Field(default_factory=ConfidentText)
    timezone: ConfidentText = Field(default_factory=ConfidentText)
    language: ConfidentText = Field(default_factory=ConfidentText)
    links: list[LinkDraft] = Field(default_factory=list, max_length=30)
    experiences: list[ExperienceDraft] = Field(default_factory=list, max_length=40)
    projects: list[ProjectDraft] = Field(default_factory=list, max_length=40)
    education: list[EducationDraft] = Field(default_factory=list, max_length=30)
    certifications: list[CertificationDraft] = Field(default_factory=list, max_length=40)
    languages: list[LanguageDraft] = Field(default_factory=list, max_length=30)
    skills: list[SkillDraft] = Field(default_factory=list, max_length=80)

    def low_confidence_paths(self, threshold: float = LOW_CONFIDENCE) -> list[str]:
        paths: list[str] = []
        for name in (
            "display_name",
            "headline",
            "summary",
            "location",
            "timezone",
            "language",
        ):
            field: ConfidentText = getattr(self, name)
            if field.value is not None and field.confidence < threshold:
                paths.append(name)
        for i, link in enumerate(self.links):
            if link.confidence < threshold:
                paths.append(f"links.{i}")
        for section in (
            "experiences",
            "projects",
            "education",
            "certifications",
            "languages",
            "skills",
        ):
            for i, item in enumerate(getattr(self, section)):
                if getattr(item, "confidence", 1.0) < threshold:
                    paths.append(f"{section}.{i}")
                bullets = getattr(item, "bullets", None)
                if bullets:
                    for j, b in enumerate(bullets):
                        if b.confidence < threshold:
                            paths.append(f"{section}.{i}.bullets.{j}")
        return paths
