"""Source health + track source settings + start discovery."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import DiscoveryRun, Job, TrackJob
from app.sources.discover import run_discover_track
from app.sources.models import Source, TrackSource
from app.tracks import models as track_models


async def list_source_health(session) -> list[Source]:
    return list((await session.execute(select(Source).order_by(Source.key))).scalars())


async def list_track_sources(ctx: WorkspaceContext, track_id: uuid.UUID) -> list[dict]:
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    rows = (
        await ctx.session.execute(
            select(TrackSource, Source)
            .join(Source)
            .where(TrackSource.track_id == track_id)
            .order_by(Source.key)
        )
    ).all()
    if not rows:
        # Default: enable all global ATS+board sources
        sources = (
            await ctx.session.execute(
                select(Source).where(
                    Source.enabled_global.is_(True), Source.kind.in_(("ats", "board"))
                )
            )
        ).scalars()
        for src in sources:
            ctx.session.add(
                TrackSource(
                    workspace_id=ctx.workspace_id,
                    track_id=track_id,
                    source_id=src.id,
                    enabled=True,
                    params={},
                )
            )
        await ctx.session.flush()
        rows = (
            await ctx.session.execute(
                select(TrackSource, Source)
                .join(Source)
                .where(TrackSource.track_id == track_id)
                .order_by(Source.key)
            )
        ).all()
    return [
        {
            "id": ts.id,
            "source_id": ts.source_id,
            "source_key": src.key,
            "enabled": ts.enabled,
            "params": ts.params,
        }
        for ts, src in rows
    ]


async def update_track_source(
    ctx: WorkspaceContext,
    track_id: uuid.UUID,
    source_id: uuid.UUID,
    *,
    enabled: bool | None,
    params: dict | None,
) -> dict:
    ts = (
        await ctx.session.execute(
            select(TrackSource).where(
                TrackSource.track_id == track_id, TrackSource.source_id == source_id
            )
        )
    ).scalar_one_or_none()
    if ts is None or ts.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track source not found", 404)
    if enabled is not None:
        ts.enabled = enabled
    if params is not None:
        ts.params = params
    await ctx.session.flush()
    src = await ctx.session.get(Source, source_id)
    await audit.record(
        ctx,
        action="track_source.updated",
        target_type="track_source",
        target_id=str(ts.id),
        after={"enabled": ts.enabled},
    )
    return {
        "id": ts.id,
        "source_id": ts.source_id,
        "source_key": src.key if src else "",
        "enabled": ts.enabled,
        "params": ts.params,
    }


async def start_discovery(
    ctx: WorkspaceContext,
    track_id: uuid.UUID,
    *,
    fixture_root: Path | None = None,
    background: bool = True,
) -> DiscoveryRun:
    from datetime import UTC, datetime

    from sqlalchemy import func, select

    from app.schedules.cron import day_start_utc
    from app.schedules.models import Schedule

    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    if track.status == "archived":
        raise AppError("conflict", "Archived track cannot run", 409)

    # Run now bypasses schedule timing but not daily caps.
    now = datetime.now(UTC)
    schedules = list(
        (
            await ctx.session.execute(
                select(Schedule).where(
                    Schedule.track_id == track_id,
                    Schedule.workspace_id == ctx.workspace_id,
                )
            )
        )
        .scalars()
        .all()
    )
    if schedules:
        # Use the strictest cap / first schedule timezone
        cap = min(s.daily_cap for s in schedules)
        tz_name = schedules[0].timezone or "UTC"
        start = day_start_utc(now, tz_name)
        used = int(
            (
                await ctx.session.execute(
                    select(func.count())
                    .select_from(DiscoveryRun)
                    .where(
                        DiscoveryRun.track_id == track_id,
                        DiscoveryRun.workspace_id == ctx.workspace_id,
                        DiscoveryRun.created_at >= start,
                    )
                )
            ).scalar_one()
        )
        if used >= cap:
            raise AppError("rate_limited", "Daily run cap reached", 429)

    run = DiscoveryRun(
        workspace_id=ctx.workspace_id,
        track_id=track_id,
        status="queued",
        trigger="run_now",
        progress={"boards_checked": 0, "jobs_found": 0, "jobs_new": 0, "linked": 0},
    )
    ctx.session.add(run)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="discovery.run_started",
        target_type="discovery_run",
        target_id=str(run.id),
        after={"track_id": str(track_id), "trigger": "run_now"},
    )
    # Run inline for request durability in tests; production uses DBOS enqueue.
    await run_discover_track(ctx, track_id, run_id=run.id, fixture_root=fixture_root, board_limit=8)
    await ctx.session.refresh(run)
    return run


async def get_run(ctx: WorkspaceContext, run_id: uuid.UUID) -> DiscoveryRun:
    run = await ctx.session.get(DiscoveryRun, run_id)
    if run is None or run.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Run not found", 404)
    return run


async def list_track_jobs(ctx: WorkspaceContext, track_id: uuid.UUID) -> list[dict]:
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    rows = (
        await ctx.session.execute(
            select(TrackJob, Job)
            .join(Job, Job.id == TrackJob.job_id)
            .where(TrackJob.track_id == track_id, Job.status == "open")
            .order_by(TrackJob.created_at.desc())
            .limit(100)
        )
    ).all()
    out = []
    for tj, job in rows:
        company_name = None
        if job.company_id:
            from app.companies.models import Company

            c = await ctx.session.get(Company, job.company_id)
            company_name = c.name if c else None
        out.append(
            {
                "id": tj.id,
                "track_id": tj.track_id,
                "job_id": tj.job_id,
                "score": tj.score,
                "status": tj.status,
                "title": job.title,
                "company_name": company_name,
                "apply_url": job.apply_url,
                "work_mode": job.work_mode,
            }
        )
    return out
