"""Onboarding plan request and response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class OnboardingPlanBody(BaseModel):
    resume_text: str | None = Field(default=None, max_length=20_000)
    role_text: str | None = Field(default=None, max_length=8000)
    profile_id: str | None = None
    timezone: str = Field(default="UTC", max_length=64)


class ResumeBasics(BaseModel):
    name: str = ""
    email: str = ""
    headline: str = ""
    location: str = ""
    skills: list[str] = Field(default_factory=list)
    years: int | None = None


class ScheduleDefaults(BaseModel):
    preset: str = "every_4_hours"
    timezone: str = "UTC"
    quiet_hours: dict[str, str] = Field(default_factory=lambda: {"start": "22:00", "end": "07:00"})
    daily_cap: int = 12


class OnboardingPlanRead(BaseModel):
    basics: ResumeBasics
    answers: list[dict[str, Any]] = Field(default_factory=list)
    search: dict[str, Any] | None = None
    schedule: ScheduleDefaults
    source: Literal["defaults", "ai"] = "defaults"
