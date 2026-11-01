"""Schedule CRUD + run history + pause helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import DiscoveryRun
from app.schedules import cron as cron_util
from app.schedules.models import Schedule
from app.sources.models import Source
from app.tracks import models as track_models


def _read(row: Schedule) -> dict[str, Any]:
    quiet = row.quiet_hours or {}
    return {
        "id": row.id,
        "track_id": row.track_id,
        "scope": row.scope,
        "source_id": row.source_id,
        "preset": row.preset,
        "cron": row.cron,
        "timezone": row.timezone,
        "quiet_hours": quiet,
        "daily_cap": row.daily_cap,
        "enabled": row.enabled,
        "next_run_at": row.next_run_at,
        "last_run_at": row.last_run_at,
        "last_skip_reason": row.last_skip_reason or "",
        "preview": cron_util.human_preview(row.cron, row.timezone, quiet),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


async def _get_track(ctx: WorkspaceContext, track_id: uuid.UUID) -> track_models.Track:
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    return track


async def list_schedules(ctx: WorkspaceContext, track_id: uuid.UUID) -> list[dict[str, Any]]:
    await _get_track(ctx, track_id)
    rows = (
        (
            await ctx.session.execute(
                select(Schedule)
                .where(Schedule.track_id == track_id, Schedule.workspace_id == ctx.workspace_id)
                .order_by(Schedule.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return [_read(r) for r in rows]


async def create_schedule(
    ctx: WorkspaceContext, track_id: uuid.UUID, body: dict[str, Any]
) -> dict[str, Any]:
    track = await _get_track(ctx, track_id)
    scope = body.get("scope") or "all"
    source_id = body.get("source_id")
    if scope == "source":
        if source_id is None:
            raise AppError("validation_error", "source_id required when scope=source", 422)
        src = await ctx.session.get(Source, source_id)
        if src is None:
            raise AppError("not_found", "Source not found", 404)
    elif source_id is not None:
        raise AppError("validation_error", "source_id only valid when scope=source", 422)

    preset, cron = cron_util.resolve_cron(preset=body.get("preset"), cron=body.get("cron"))
    tz = cron_util.validate_timezone(body.get("timezone") or "UTC")
    raw_quiet = body.get("quiet_hours") or {}
    quiet: dict[str, Any]
    if isinstance(raw_quiet, dict):
        quiet = dict(raw_quiet)
    else:
        quiet = {"start": getattr(raw_quiet, "start", ""), "end": getattr(raw_quiet, "end", "")}
        quiet = {k: v for k, v in quiet.items() if v}
    if quiet:
        cron_util.in_quiet_hours(datetime.now(UTC), tz, quiet)

    now = datetime.now(UTC)
    next_at = cron_util.next_fire(cron, tz, now)
    if quiet and cron_util.in_quiet_hours(next_at, tz, quiet):
        next_at = cron_util.end_of_quiet_hours(next_at, tz, quiet)

    row = Schedule(
        workspace_id=ctx.workspace_id,
        track_id=track.id,
        scope=scope,
        source_id=source_id if scope == "source" else None,
        preset=preset,
        cron=cron,
        timezone=tz,
        quiet_hours=quiet,
        daily_cap=int(body.get("daily_cap", 12)),
        enabled=bool(body.get("enabled", True)) and track.status == "active",
        next_run_at=next_at,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="schedule.created",
        target_type="schedule",
        target_id=str(row.id),
        after={"track_id": str(track_id), "cron": cron, "timezone": tz},
    )
    return _read(row)


async def update_schedule(
    ctx: WorkspaceContext, schedule_id: uuid.UUID, body: dict[str, Any]
) -> dict[str, Any]:
    row = await ctx.session.get(Schedule, schedule_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Schedule not found", 404)
    track = await _get_track(ctx, row.track_id)
    before = {"cron": row.cron, "enabled": row.enabled, "timezone": row.timezone}

    if body.get("scope") is not None:
        row.scope = body["scope"]
    if "source_id" in body:
        row.source_id = body["source_id"] if row.scope == "source" else None
    if body.get("preset") is not None or body.get("cron") is not None:
        preset, cron = cron_util.resolve_cron(
            preset=body.get("preset") or row.preset, cron=body.get("cron") or row.cron
        )
        row.preset = preset
        row.cron = cron
    if body.get("timezone") is not None:
        row.timezone = cron_util.validate_timezone(body["timezone"])
    if "quiet_hours" in body and body["quiet_hours"] is not None:
        q = body["quiet_hours"]
        row.quiet_hours = q if isinstance(q, dict) else q.model_dump()
    if body.get("daily_cap") is not None:
        row.daily_cap = int(body["daily_cap"])
    if body.get("enabled") is not None:
        row.enabled = bool(body["enabled"]) and track.status == "active"

    # Recompute next run on any timing change
    now = datetime.now(UTC)
    next_at = cron_util.next_fire(row.cron, row.timezone, now)
    if cron_util.in_quiet_hours(next_at, row.timezone, row.quiet_hours):
        next_at = cron_util.end_of_quiet_hours(next_at, row.timezone, row.quiet_hours)
    row.next_run_at = next_at
    row.last_skip_reason = ""
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="schedule.updated",
        target_type="schedule",
        target_id=str(row.id),
        before=before,
        after={"cron": row.cron, "enabled": row.enabled, "timezone": row.timezone},
    )
    return _read(row)


async def delete_schedule(ctx: WorkspaceContext, schedule_id: uuid.UUID) -> None:
    row = await ctx.session.get(Schedule, schedule_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Schedule not found", 404)
    await audit.record(
        ctx,
        action="schedule.deleted",
        target_type="schedule",
        target_id=str(row.id),
        before={"track_id": str(row.track_id)},
    )
    await ctx.session.delete(row)


async def pause_track(ctx: WorkspaceContext, track_id: uuid.UUID) -> track_models.Track:
    track = await _get_track(ctx, track_id)
    if track.status == "archived":
        raise AppError("conflict", "Archived track cannot be paused", 409)
    track.status = "paused"
    rows = (
        (await ctx.session.execute(select(Schedule).where(Schedule.track_id == track_id)))
        .scalars()
        .all()
    )
    for s in rows:
        s.enabled = False
        s.last_skip_reason = "track_paused"
    await audit.record(
        ctx,
        action="track.paused",
        target_type="track",
        target_id=str(track_id),
    )
    await ctx.session.flush()
    await ctx.session.refresh(track)
    return track


async def resume_track(ctx: WorkspaceContext, track_id: uuid.UUID) -> track_models.Track:
    track = await _get_track(ctx, track_id)
    if track.status != "paused":
        raise AppError("conflict", "Track is not paused", 409)
    track.status = "active"
    now = datetime.now(UTC)
    rows = (
        (await ctx.session.execute(select(Schedule).where(Schedule.track_id == track_id)))
        .scalars()
        .all()
    )
    for s in rows:
        s.enabled = True
        s.next_run_at = cron_util.next_fire(s.cron, s.timezone, now)
        s.last_skip_reason = ""
    await audit.record(
        ctx,
        action="track.resumed",
        target_type="track",
        target_id=str(track_id),
    )
    await ctx.session.flush()
    await ctx.session.refresh(track)
    return track


async def list_run_history(
    ctx: WorkspaceContext, track_id: uuid.UUID, *, limit: int = 50
) -> list[dict[str, Any]]:
    await _get_track(ctx, track_id)
    rows = (
        (
            await ctx.session.execute(
                select(DiscoveryRun)
                .where(
                    DiscoveryRun.track_id == track_id,
                    DiscoveryRun.workspace_id == ctx.workspace_id,
                )
                .order_by(DiscoveryRun.created_at.desc())
                .limit(min(limit, 100))
            )
        )
        .scalars()
        .all()
    )
    out = []
    for r in rows:
        duration = None
        if r.started_at and r.finished_at:
            duration = int((r.finished_at - r.started_at).total_seconds() * 1000)
        out.append(
            {
                "id": r.id,
                "track_id": r.track_id,
                "status": r.status,
                "trigger": r.trigger,
                "progress": r.progress or {},
                "error": r.error,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "created_at": r.created_at,
                "duration_ms": duration,
            }
        )
    return out


async def count_runs_today(
    ctx: WorkspaceContext, track_id: uuid.UUID, *, tz_name: str, now: datetime
) -> int:
    start = cron_util.day_start_utc(now, tz_name)
    return int(
        (
            await ctx.session.execute(
                select(func.count())
                .select_from(DiscoveryRun)
                .where(
                    DiscoveryRun.track_id == track_id,
                    DiscoveryRun.workspace_id == ctx.workspace_id,
                    DiscoveryRun.created_at >= start,
                    DiscoveryRun.trigger.in_(("schedule", "manual", "run_now")),
                )
            )
        ).scalar_one()
    )
