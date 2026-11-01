"""Gap plan: track must-skills not present on the profile."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.gaps import models as m
from app.gaps.schemas import GapPlanItemRead
from app.gaps.suggest import suggest_for_skill
from app.profiles.models import Skill
from app.tracks.models import Track, TrackCriteria


async def _track(ctx: WorkspaceContext, track_id: uuid.UUID) -> Track:
    track = await ctx.session.get(Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    return track


def _read(row: m.GapPlanItem) -> GapPlanItemRead:
    return GapPlanItemRead.model_validate(row)


async def list_items(ctx: WorkspaceContext, track_id: uuid.UUID) -> list[GapPlanItemRead]:
    await _track(ctx, track_id)
    rows = list(
        (
            await ctx.session.execute(
                select(m.GapPlanItem)
                .where(
                    m.GapPlanItem.workspace_id == ctx.workspace_id,
                    m.GapPlanItem.track_id == track_id,
                )
                .order_by(m.GapPlanItem.created_at)
            )
        ).scalars()
    )
    return [_read(r) for r in rows]


async def refresh_suggestions(ctx: WorkspaceContext, track_id: uuid.UUID) -> list[GapPlanItemRead]:
    track = await _track(ctx, track_id)
    criteria = (
        await ctx.session.execute(select(TrackCriteria).where(TrackCriteria.track_id == track_id))
    ).scalar_one_or_none()
    structured = (criteria.structured if criteria else {}) or {}
    skills_block = structured.get("skills") or {}
    must = list(skills_block.get("must") or [])

    have = {
        (s.name or "").casefold()
        for s in (
            await ctx.session.execute(
                select(Skill).where(
                    Skill.profile_id == track.profile_id, Skill.do_not_use.is_(False)
                )
            )
        ).scalars()
        if s.name
    }

    existing = {
        r.skill.casefold(): r
        for r in (
            await ctx.session.execute(
                select(m.GapPlanItem).where(
                    m.GapPlanItem.workspace_id == ctx.workspace_id,
                    m.GapPlanItem.track_id == track_id,
                )
            )
        ).scalars()
    }

    created = 0
    for skill in must:
        if not skill or skill.casefold() in have:
            continue
        if skill.casefold() in existing:
            continue
        suggestion, url = suggest_for_skill(skill)
        row = m.GapPlanItem(
            workspace_id=ctx.workspace_id,
            track_id=track_id,
            skill=skill,
            suggestion=suggestion,
            resource_url=url,
            status="open",
        )
        ctx.session.add(row)
        created += 1

    await audit.record(
        ctx,
        action="gap_plan.refreshed",
        target_type="track",
        target_id=str(track_id),
        after={"created": created},
    )
    await ctx.session.flush()
    return await list_items(ctx, track_id)


async def update_status(
    ctx: WorkspaceContext, item_id: uuid.UUID, *, status: str
) -> GapPlanItemRead:
    row = await ctx.session.get(m.GapPlanItem, item_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Gap item not found", 404)
    before = row.status
    row.status = status
    row.completed_at = datetime.now(UTC) if status == "done" else None
    await audit.record(
        ctx,
        action="gap_plan.status_changed",
        target_type="gap_plan_item",
        target_id=str(row.id),
        before={"status": before},
        after={"status": status},
    )
    await ctx.session.flush()
    return _read(row)
