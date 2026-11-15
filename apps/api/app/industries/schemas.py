"""API schemas for industry packs and the resolved experience manifest."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RoleFamilyRead(BaseModel):
    key: str
    label_key: str
    titles: list[str] = Field(default_factory=list)


class IndustrySummary(BaseModel):
    key: str
    label_key: str
    icon: str
    role_families: list[RoleFamilyRead] = Field(default_factory=list)


class IndustryList(BaseModel):
    items: list[IndustrySummary]


class WorkspaceIndustryRead(BaseModel):
    key: str
    label_key: str
    icon: str
    is_primary: bool
    custom: bool = False


class WorkspaceIndustryList(BaseModel):
    items: list[WorkspaceIndustryRead]


class IndustryAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=48)
    is_primary: bool = False


class IndustryPrimaryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=48)


class IndustryExperienceRead(BaseModel):
    """Global manifest plus one manifest per enabled pack for per-search pages."""

    primary: str
    enabled: list[WorkspaceIndustryRead]
    manifest: dict[str, Any]
    packs: dict[str, dict[str, Any]]


class IndustryDetectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)


class IndustryDetectRead(BaseModel):
    pack_key: str
    role_family: str | None
    confidence: float
    reasons: list[str] = Field(default_factory=list)


class CustomPackDraftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=3, max_length=600)
    base_pack: str | None = Field(default=None, max_length=48)


class CustomPackDraftRead(BaseModel):
    key: str
    base_pack: str
    role_family: str | None
    pack: dict[str, Any]


class CustomPackAcceptIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=48, pattern=r"^custom_[a-z0-9_]+$")
    pack: dict[str, Any]
