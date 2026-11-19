"""Typed values per bundle target, so apply never trusts a raw `Any`.

Every target re-validates through the same create or update schema its service uses. An unknown
target or an invalid value is a bundle bug and fails the draft before the review screen.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.auth.schemas import MeUpdate
from app.core.errors import AppError
from app.profiles import schemas as p
from app.profiles.answer_keys import CANONICAL_BY_KEY
from app.profiles.answers import validate_key_country
from app.profiles.schemas import VoicePresetBody, VoiceUpdate
from app.tracks.criteria import CriteriaV1


class TargetError(ValueError):
    """A bundle value that does not match its target schema."""


@dataclass(frozen=True)
class TargetSpec:
    kind: str
    validate: Callable[[Any], Any]


class StudioBaseResume(BaseModel):
    """Not a persisted model: this describes the base resume setup creates in Studio."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=200)
    template: str = Field(default="classic", max_length=40)
    page_size: str = Field(default="a4", pattern="^(letter|a4)$")


def _wrap(model: type[BaseModel], **payload: Any) -> Any:
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise TargetError(str(exc)) from exc


def _profile_field(field: str) -> Callable[[Any], Any]:
    def validate(value: Any) -> Any:
        return getattr(_wrap(p.ProfileUpdate, **{field: value}), field)

    return validate


def _entity(model: type[BaseModel]) -> Callable[[Any], Any]:
    def validate(value: Any) -> Any:
        if not isinstance(value, dict):
            raise TargetError("an entity target needs an object")
        return _wrap(model, **value).model_dump(mode="json")

    return validate


def _answer(target: str, value: Any) -> Any:
    parts = target.split(".")
    if len(parts) not in (2, 3) or not parts[1]:
        raise TargetError("answer targets look like answers.<key> or answers.<key>.<CC>")
    key = parts[1]
    country = parts[2].upper() if len(parts) == 3 else None
    if not isinstance(value, dict):
        raise TargetError("an answer target needs {answer, approved}")
    try:
        validate_key_country(key, country)
    except AppError as exc:
        raise TargetError(str(exc.message)) from exc
    meta = CANONICAL_BY_KEY.get(key)
    if meta is not None and meta.country_scoped and not country:
        raise TargetError(f"{key} needs a country in the target")
    answer = value.get("answer")
    if not isinstance(answer, str) or len(answer) > 4000:
        raise TargetError("an answer must be a string of at most 4000 characters")
    approved = value.get("approved", False)
    if not isinstance(approved, bool):
        raise TargetError("approved must be a boolean")
    return {"answer": answer, "approved": approved}


def _industry(value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        raise TargetError("industry needs a label")
    if len(value) > 120:
        raise TargetError("industry label is too long")
    return value.strip()


TARGETS: dict[str, TargetSpec] = {
    "profile.display_name": TargetSpec("value", _profile_field("display_name")),
    "profile.headline": TargetSpec("value", _profile_field("headline")),
    "profile.summary": TargetSpec("value", _profile_field("summary")),
    "profile.location": TargetSpec("value", _profile_field("location")),
    "profile.timezone": TargetSpec("value", _profile_field("timezone")),
    "profile.language": TargetSpec("value", _profile_field("language")),
    "profile.links": TargetSpec("list", _profile_field("links")),
    "profile.salary_prefs": TargetSpec("value", _profile_field("salary_prefs")),
    "profile.work_authorization": TargetSpec("value", _profile_field("work_authorization")),
    "profile.experience": TargetSpec("entity", _entity(p.ExperienceIn)),
    "profile.project": TargetSpec("entity", _entity(p.ProjectIn)),
    "profile.education": TargetSpec("entity", _entity(p.EducationIn)),
    "profile.certification": TargetSpec("entity", _entity(p.CertificationIn)),
    "profile.spoken_language": TargetSpec("entity", _entity(p.LanguageIn)),
    "profile.skill": TargetSpec("entity", _entity(p.SkillIn)),
    "writing.preset": TargetSpec(
        "value", lambda value: _wrap(VoicePresetBody, preset=value).preset
    ),
    "writing.banned_phrases": TargetSpec(
        "list", lambda value: _wrap(VoiceUpdate, banned_phrases=value).banned_phrases
    ),
    "studio.base_resume": TargetSpec(
        "value", lambda value: _wrap(StudioBaseResume, **(value or {})).model_dump(mode="json")
    ),
    "account.name": TargetSpec("value", lambda value: _wrap(MeUpdate, name=value).name),
    "account.timezone": TargetSpec("value", lambda value: _wrap(MeUpdate, timezone=value).timezone),
    "industry.field": TargetSpec("value", _industry),
    "search.criteria": TargetSpec("value", lambda value: _wrap(CriteriaV1, **(value or {}))),
}


def validate_target(target: str, value: Any) -> Any:
    """Validate one bundle value against its target. Raises `TargetError`."""
    if target.startswith("answers."):
        return _answer(target, value)
    spec = TARGETS.get(target)
    if spec is None:
        raise TargetError(f"unknown target {target!r}")
    return spec.validate(value)


def answer_needs_country(target: str) -> bool:
    """A country-scoped answer target that carries no country: the human must pick one."""
    parts = target.split(".")
    if len(parts) != 2 or parts[0] != "answers":
        return False
    meta = CANONICAL_BY_KEY.get(parts[1])
    return bool(meta and meta.country_scoped)


def answer_target_with_country(target: str, country: str | None) -> str:
    """Qualify a country-less country-scoped answer target with the chosen country."""
    if not country or not answer_needs_country(target):
        return target
    return f"{target}.{country.upper()}"


def target_kind(target: str) -> str:
    if target.startswith("answers."):
        return "value"
    spec = TARGETS.get(target)
    return spec.kind if spec else "value"


__all__ = [
    "TARGETS",
    "StudioBaseResume",
    "TargetError",
    "answer_needs_country",
    "answer_target_with_country",
    "target_kind",
    "validate_target",
]
