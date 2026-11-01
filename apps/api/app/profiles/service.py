"""Career Profile persistence. All reads and writes go through the request's RLS-scoped session;
every mutation appends an activity_log row with ids and field names only, never resume text."""

import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import DeclarativeBase

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as m
from app.profiles import schemas as s

PROFILE_LIMIT = 10  # profile selector exists from day one; coach workspaces raise this later


async def profile_has_facts(ctx: WorkspaceContext, profile_id: uuid.UUID) -> bool:
    """True when any fact section has rows (used to require merge instead of blind confirm)."""
    for model in (
        m.Experience,
        m.Project,
        m.Education,
        m.Certification,
        m.Language,
        m.Skill,
    ):
        n = (
            await ctx.session.execute(
                select(func.count()).select_from(model).where(model.profile_id == profile_id)  # type: ignore[attr-defined]
            )
        ).scalar_one()
        if n:
            return True
    return False


@dataclass(frozen=True)
class Section:
    key: str
    model: type[DeclarativeBase]
    create: type[BaseModel]
    patch: type[BaseModel]
    read: type[BaseModel]
    order: tuple[Any, ...]


def _order(model: Any, *cols: str) -> tuple[Any, ...]:
    return (
        model.sort_order,
        *(getattr(model, c).desc().nulls_last() for c in cols),
        model.created_at,
    )


SECTIONS: dict[str, Section] = {
    sec.key: sec
    for sec in (
        Section(
            "experiences",
            m.Experience,
            s.ExperienceIn,
            s.ExperiencePatch,
            s.ExperienceRead,
            _order(m.Experience, "end_date", "start_date"),
        ),
        Section(
            "projects",
            m.Project,
            s.ProjectIn,
            s.ProjectPatch,
            s.ProjectRead,
            _order(m.Project, "end_date"),
        ),
        Section("bullets", m.Bullet, s.BulletIn, s.BulletPatch, s.BulletRead, _order(m.Bullet)),
        Section(
            "education",
            m.Education,
            s.EducationIn,
            s.EducationPatch,
            s.EducationRead,
            _order(m.Education, "end_date"),
        ),
        Section(
            "certifications",
            m.Certification,
            s.CertificationIn,
            s.CertificationPatch,
            s.CertificationRead,
            _order(m.Certification, "issued_on"),
        ),
        Section(
            "languages",
            m.Language,
            s.LanguageIn,
            s.LanguagePatch,
            s.LanguageRead,
            _order(m.Language),
        ),
        Section("skills", m.Skill, s.SkillIn, s.SkillPatch, s.SkillRead, _order(m.Skill)),
    )
}


def evidence_strength(text: str, metrics: list[dict[str, Any]]) -> str:
    """Cheap, explainable heuristic: a stated metric is strong, any number is ok, else weak."""
    if metrics:
        return "strong"
    return "ok" if any(ch.isdigit() for ch in text) else "weak"


async def _get_profile(ctx: WorkspaceContext, profile_id: uuid.UUID) -> m.CandidateProfile:
    row = await ctx.session.get(m.CandidateProfile, profile_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("profile_not_found", "Profile not found", 404)
    return row


async def list_profiles(ctx: WorkspaceContext) -> list[m.CandidateProfile]:
    q = select(m.CandidateProfile).order_by(
        m.CandidateProfile.is_default.desc(), m.CandidateProfile.created_at
    )
    return list((await ctx.session.execute(q)).scalars())


async def create_profile(ctx: WorkspaceContext, body: s.ProfileCreate) -> m.CandidateProfile:
    count = (
        await ctx.session.execute(select(func.count()).select_from(m.CandidateProfile))
    ).scalar_one()
    if count >= PROFILE_LIMIT:
        raise AppError("profile_limit", "Profile limit reached", 409, {"cap": PROFILE_LIMIT})
    row = m.CandidateProfile(
        workspace_id=ctx.workspace_id,
        created_by=ctx.user_id,
        is_default=count == 0,
        minimization=s.Minimization().model_dump(),
        **body.model_dump(),
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(ctx, action="profile.created", target_type="profile", target_id=str(row.id))
    return row


async def get_profile(ctx: WorkspaceContext, profile_id: uuid.UUID) -> m.CandidateProfile:
    return await _get_profile(ctx, profile_id)


async def update_profile(
    ctx: WorkspaceContext, profile_id: uuid.UUID, body: s.ProfileUpdate
) -> m.CandidateProfile:
    row = await _get_profile(ctx, profile_id)
    changes = body.model_dump(exclude_unset=True)
    if "display_name" in changes and changes["display_name"] is None:
        raise AppError("validation_error", "display_name cannot be empty", 422)
    for key, value in changes.items():
        setattr(row, key, value)
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="profile.updated",
        target_type="profile",
        target_id=str(row.id),
        after={"fields": sorted(changes)},
    )
    return row


async def delete_profile(ctx: WorkspaceContext, profile_id: uuid.UUID) -> None:
    row = await _get_profile(ctx, profile_id)
    was_default = row.is_default
    await ctx.session.delete(row)
    await ctx.session.flush()
    if was_default:
        nxt = (
            await ctx.session.execute(
                select(m.CandidateProfile).order_by(m.CandidateProfile.created_at).limit(1)
            )
        ).scalar_one_or_none()
        if nxt is not None:
            nxt.is_default = True
    await audit.record(
        ctx, action="profile.deleted", target_type="profile", target_id=str(profile_id)
    )


async def full_profile(ctx: WorkspaceContext, profile_id: uuid.UUID) -> dict[str, Any]:
    profile = await _get_profile(ctx, profile_id)
    out: dict[str, Any] = {"profile": profile}
    for key, sec in SECTIONS.items():
        q = select(sec.model).where(sec.model.profile_id == profile_id).order_by(*sec.order)  # type: ignore[attr-defined]
        out[key] = list((await ctx.session.execute(q)).scalars())
    return out


async def list_section(
    ctx: WorkspaceContext, profile_id: uuid.UUID, key: str
) -> list[DeclarativeBase]:
    await _get_profile(ctx, profile_id)
    sec = SECTIONS[key]
    q = select(sec.model).where(sec.model.profile_id == profile_id).order_by(*sec.order)  # type: ignore[attr-defined]
    return list((await ctx.session.execute(q)).scalars())


async def _check_parent(ctx: WorkspaceContext, profile_id: uuid.UUID, data: dict[str, Any]) -> None:
    """A bullet's parent must be an experience or project of the same profile."""
    for field, model in (("experience_id", m.Experience), ("project_id", m.Project)):
        pid = data.get(field)
        if pid is None:
            continue
        parent = await ctx.session.get(model, pid)
        if parent is None or parent.profile_id != profile_id:
            raise AppError("parent_not_found", "Parent entry not found", 404)


def _prepare(key: str, data: dict[str, Any]) -> dict[str, Any]:
    if key == "bullets":
        data["evidence_strength"] = evidence_strength(data["text"], data.get("metrics", []))
    return data


async def create_item(
    ctx: WorkspaceContext, profile_id: uuid.UUID, key: str, body: BaseModel
) -> DeclarativeBase:
    await _get_profile(ctx, profile_id)
    sec = SECTIONS[key]
    data = _prepare(key, body.model_dump())
    if key == "bullets":
        await _check_parent(ctx, profile_id, data)
    row = sec.model(workspace_id=ctx.workspace_id, profile_id=profile_id, **data)
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action=f"profile.{key}.created",
        target_type=key,
        target_id=str(row.id),  # type: ignore[attr-defined]
        after={"profile_id": str(profile_id), "source": data.get("source")},
    )
    return row


async def _get_item(
    ctx: WorkspaceContext, profile_id: uuid.UUID, key: str, item_id: uuid.UUID
) -> DeclarativeBase:
    row = await ctx.session.get(SECTIONS[key].model, item_id)
    if row is None or row.profile_id != profile_id or row.workspace_id != ctx.workspace_id:  # type: ignore[attr-defined]
        raise AppError("item_not_found", "Entry not found", 404)
    return row


async def update_item(
    ctx: WorkspaceContext, profile_id: uuid.UUID, key: str, item_id: uuid.UUID, body: BaseModel
) -> DeclarativeBase:
    sec = SECTIONS[key]
    row = await _get_item(ctx, profile_id, key, item_id)
    changes = body.model_dump(exclude_unset=True)
    current = {f: getattr(row, f) for f in sec.create.model_fields}
    merged = {**current, **changes}
    try:
        validated = sec.create.model_validate(merged).model_dump()
    except ValidationError as exc:
        raise AppError(
            "validation_error",
            "Invalid entry",
            422,
            exc.errors(include_url=False, include_context=False, include_input=False),
        ) from None
    if key == "bullets":
        await _check_parent(ctx, profile_id, validated)
        validated = _prepare(key, validated)
        changes["evidence_strength"] = validated["evidence_strength"]
    for field in changes:
        setattr(row, field, validated.get(field, changes[field]))
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action=f"profile.{key}.updated",
        target_type=key,
        target_id=str(item_id),
        after={"profile_id": str(profile_id), "fields": sorted(changes)},
    )
    return row


async def delete_item(
    ctx: WorkspaceContext, profile_id: uuid.UUID, key: str, item_id: uuid.UUID
) -> None:
    row = await _get_item(ctx, profile_id, key, item_id)
    await ctx.session.delete(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action=f"profile.{key}.deleted",
        target_type=key,
        target_id=str(item_id),
        after={"profile_id": str(profile_id)},
    )
