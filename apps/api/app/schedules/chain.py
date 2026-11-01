"""Automation chain: discover → score → risk → (prepare) → notify."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.applications import service as apps_svc
from app.applications.models import TailorRun
from app.core.mail import Mailer
from app.core.security import WorkspaceContext
from app.jobs.models import DiscoveryRun, Job, TrackJob
from app.notifications import service as notif
from app.safety import service as safety_svc
from app.safety.models import JobRisk
from app.sources.discover import run_discover_track
from app.tracks import models as track_models

logger = logging.getLogger(__name__)

DEFAULT_SCORE_THRESHOLD = 0.65
DEFAULT_PREPARE_TOP_K = 5
WS_CONCURRENCY_LIMIT = 2


async def active_run_count(ctx: WorkspaceContext) -> int:
    rows = (
        (
            await ctx.session.execute(
                select(DiscoveryRun).where(
                    DiscoveryRun.workspace_id == ctx.workspace_id,
                    DiscoveryRun.status.in_(("queued", "running")),
                )
            )
        )
        .scalars()
        .all()
    )
    return len(list(rows))


async def has_active_track_run(ctx: WorkspaceContext, track_id: uuid.UUID) -> bool:
    row = (
        await ctx.session.execute(
            select(DiscoveryRun).where(
                DiscoveryRun.track_id == track_id,
                DiscoveryRun.workspace_id == ctx.workspace_id,
                DiscoveryRun.status.in_(("queued", "running")),
            )
        )
    ).scalar_one_or_none()
    return row is not None


async def run_automation_chain(
    ctx: WorkspaceContext,
    track_id: uuid.UUID,
    *,
    trigger: str = "schedule",
    source_id: uuid.UUID | None = None,
    mailer: Mailer | None = None,
    board_limit: int = 6,
    bypass_schedule: bool = False,
) -> DiscoveryRun:
    """Full chain. Never auto-submits. Prepare only drafts tailored materials."""
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise ValueError("track not found")

    run = DiscoveryRun(
        workspace_id=ctx.workspace_id,
        track_id=track_id,
        status="queued",
        trigger=trigger,
        progress={
            "boards_checked": 0,
            "jobs_found": 0,
            "jobs_new": 0,
            "linked": 0,
            "source_id": str(source_id) if source_id else None,
            "bypass_schedule": bypass_schedule,
        },
    )
    ctx.session.add(run)
    await ctx.session.flush()

    try:
        run = await run_discover_track(ctx, track_id, run_id=run.id, board_limit=board_limit)
        progress = dict(run.progress or {})

        tj_rows = list(
            (
                await ctx.session.execute(
                    select(TrackJob)
                    .where(
                        TrackJob.track_id == track_id,
                        TrackJob.workspace_id == ctx.workspace_id,
                    )
                    .order_by(TrackJob.created_at.desc())
                    .limit(40)
                )
            )
            .scalars()
            .all()
        )
        assessed = 0
        green_strong: list[TrackJob] = []
        settings = track.settings or {}
        threshold = float(settings.get("prepare_score_threshold", DEFAULT_SCORE_THRESHOLD))
        top_k = int(settings.get("prepare_top_k", DEFAULT_PREPARE_TOP_K))
        strong_threshold = float(settings.get("strong_match_threshold", threshold))

        for tj in tj_rows:
            risk = await ctx.session.get(JobRisk, tj.job_id)
            if risk is None:
                try:
                    risk = await safety_svc.assess_and_store(ctx, tj.job_id)
                    assessed += 1
                except Exception as exc:
                    progress["risk_error"] = str(exc)[:160]
                    continue
            score = float(tj.score or 0)
            if risk and risk.level == "green" and score >= threshold:
                green_strong.append(tj)
            if risk and risk.level in ("yellow", "red") and score >= strong_threshold:
                job = await ctx.session.get(Job, tj.job_id)
                title = job.title if job else "Job"
                company = (job.meta or {}).get("company_name", "Company") if job else "Company"
                await notif.emit_to_workspace_members(
                    ctx,
                    event="risk_flag",
                    title=f"Flag: {title}",
                    body=f"{company} · risk {risk.level}",
                    payload={"job_id": str(tj.job_id), "level": risk.level},
                    dedupe_key=f"risk:{tj.job_id}",
                    mailer=mailer,
                )

        progress["risk_assessed"] = assessed

        prepared = 0
        autonomy = track.autonomy or "discover"
        if autonomy in ("prepare", "assist", "auto_submit"):
            green_strong.sort(key=lambda x: float(x.score or 0), reverse=True)
            for tj in green_strong[:top_k]:
                prior = (
                    await ctx.session.execute(
                        select(TailorRun).where(
                            TailorRun.track_job_id == tj.id,
                            TailorRun.status.in_(("ready", "accepted", "running")),
                        )
                    )
                ).scalar_one_or_none()
                if prior:
                    continue
                try:
                    await apps_svc.start_tailor(ctx, tj.id, include_cover_letter=True)
                    prepared += 1
                    await notif.emit_to_workspace_members(
                        ctx,
                        event="needs_review",
                        title="Ready to review",
                        body="A tailored draft is waiting",
                        payload={"track_job_id": str(tj.id)},
                        dedupe_key=f"prepare:{tj.id}",
                        mailer=mailer,
                    )
                except Exception as exc:
                    err = str(exc)
                    if "budget" in err.lower():
                        progress["budget_stopped"] = True
                        await notif.emit_to_workspace_members(
                            ctx,
                            event="budget_reached",
                            title="Budget reached",
                            body="Automation stopped at the last free stage",
                            payload={"track_id": str(track_id)},
                            dedupe_key=f"budget:{track_id}:{datetime.now(UTC).date()}",
                            mailer=mailer,
                        )
                        break
                    progress["prepare_error"] = err[:160]
                    break
        progress["prepared"] = prepared

        strong_n = 0
        for tj in tj_rows:
            if float(tj.score or 0) >= strong_threshold:
                risk = await ctx.session.get(JobRisk, tj.job_id)
                if risk is None or risk.level == "green":
                    strong_n += 1
        if strong_n:
            await notif.emit_to_workspace_members(
                ctx,
                event="strong_match",
                title=f"{strong_n} strong match{'es' if strong_n != 1 else ''}",
                body="New jobs scored above your threshold",
                payload={"count": strong_n, "track_id": str(track_id)},
                dedupe_key=f"strong:{track_id}:{run.id}",
                mailer=None,
            )
        progress["strong_matches"] = strong_n

        run.progress = progress
        if run.status != "failed":
            run.status = "succeeded"
            run.finished_at = datetime.now(UTC)
        await ctx.session.flush()
        return run
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:500]
        run.finished_at = datetime.now(UTC)
        run.progress = {**(run.progress or {}), "chain_error": str(exc)[:200]}
        await ctx.session.flush()
        await notif.emit_to_workspace_members(
            ctx,
            event="run_failed",
            title="Discovery run failed",
            body=str(exc)[:120],
            payload={"run_id": str(run.id), "track_id": str(track_id)},
            dedupe_key=f"fail:{run.id}",
            mailer=mailer,
        )
        logger.exception("automation_chain_failed track=%s", track_id)
        return run
