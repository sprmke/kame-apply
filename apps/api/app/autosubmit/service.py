"""Evaluate and persist auto-submit policy; batch approve; anomaly pause."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.answers.models import AnswerDeskItem, AnswerDeskSession
from app.applications.models import Application
from app.audit import service as audit
from app.autosubmit import models as m
from app.autosubmit import policy as pol
from app.autosubmit.schemas import (
    AnomalyStatusRead,
    AutoSubmitSettingsRead,
    DryRunReportRead,
    PolicyVerdict,
)
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import Job, TrackJob
from app.profiles.models import AnswerBank
from app.runs.ats import detect_ats
from app.safety.models import JobRisk
from app.strategy import caps as caps_mod
from app.strategy import service as strategy_svc
from app.strategy.freshness import freshness_for
from app.tracks.models import Track
from app.workspaces.models import Workspace


def _now() -> datetime:
    return datetime.now(UTC)


def _auto_settings(track: Track) -> dict[str, Any]:
    return pol.settings_from_track(track.settings)


def _write_auto_settings(track: Track, patch: dict[str, Any]) -> dict[str, Any]:
    settings = dict(track.settings or {})
    auto = dict(settings.get("auto_submit") or {})
    auto.update(patch)
    settings["auto_submit"] = auto
    track.settings = settings
    return auto


async def get_settings(
    ctx: WorkspaceContext, track_id: uuid.UUID, settings: Settings
) -> AutoSubmitSettingsRead:
    track = await ctx.session.get(Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    auto = _auto_settings(track)
    ws = await ctx.session.get(Workspace, ctx.workspace_id)
    ws_settings = (ws.settings if ws else None) or {}
    ws_kill = bool((ws_settings.get("auto_submit") or {}).get("kill_switch", False))
    return AutoSubmitSettingsRead(
        track_id=track.id,
        autonomy=track.autonomy,
        live_enabled=auto["live_enabled"],
        dry_run_remaining=auto["dry_run_remaining"],
        score_threshold=auto["score_threshold"],
        kill_switch=auto["kill_switch"] or auto["anomaly_paused"],
        workspace_kill_switch=ws_kill,
        global_enabled=bool(getattr(settings, "auto_submit_enabled", False)),
    )


async def update_settings(
    ctx: WorkspaceContext,
    track_id: uuid.UUID,
    *,
    live_enabled: bool | None,
    dry_run_remaining: int | None,
    score_threshold: float | None,
    kill_switch: bool | None,
    settings: Settings,
) -> AutoSubmitSettingsRead:
    track = await ctx.session.get(Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    patch: dict[str, Any] = {}
    if dry_run_remaining is not None:
        patch["dry_run_remaining"] = dry_run_remaining
    if score_threshold is not None:
        patch["score_threshold"] = score_threshold
    if kill_switch is not None:
        patch["kill_switch"] = kill_switch
        if not kill_switch:
            patch["anomaly_paused"] = False
            patch["anomaly_reason"] = None
    if live_enabled is not None:
        # Enabling live requires dry-run budget exhausted (after this patch).
        if live_enabled:
            auto = _auto_settings(track)
            remaining = patch.get("dry_run_remaining", auto["dry_run_remaining"])
            if int(remaining) > 0:
                raise AppError(
                    "dry_run_required",
                    "Finish dry-run reports before enabling live auto-submit",
                    409,
                )
        patch["live_enabled"] = live_enabled
    _write_auto_settings(track, patch)
    await audit.record(
        ctx,
        action="autosubmit.settings_updated",
        target_type="track",
        target_id=str(track_id),
        after=patch,
    )
    return await get_settings(ctx, track_id, settings)


async def set_workspace_kill(ctx: WorkspaceContext, *, enabled: bool) -> None:
    ws = await ctx.session.get(Workspace, ctx.workspace_id)
    if ws is None:
        raise AppError("not_found", "Workspace not found", 404)
    settings = dict(ws.settings or {})
    auto = dict(settings.get("auto_submit") or {})
    auto["kill_switch"] = enabled
    settings["auto_submit"] = auto
    ws.settings = settings
    await audit.record(
        ctx,
        action="autosubmit.workspace_kill",
        target_type="workspace",
        target_id=str(ctx.workspace_id),
        after={"kill_switch": enabled},
    )


async def _answers_all_approved(ctx: WorkspaceContext, application_id: uuid.UUID) -> bool:
    session_ids = list(
        (
            await ctx.session.execute(
                select(AnswerDeskSession.id).where(
                    AnswerDeskSession.workspace_id == ctx.workspace_id,
                    AnswerDeskSession.application_id == application_id,
                )
            )
        ).scalars()
    )
    if not session_ids:
        return True
    items = list(
        (
            await ctx.session.execute(
                select(AnswerDeskItem).where(
                    AnswerDeskItem.workspace_id == ctx.workspace_id,
                    AnswerDeskItem.session_id.in_(session_ids),
                )
            )
        ).scalars()
    )
    free = [i for i in items if (i.question or "").strip() and not i.ai_restricted]
    if not free:
        return True
    for item in free:
        if item.answer_bank_id:
            bank = await ctx.session.get(AnswerBank, item.answer_bank_id)
            if bank and bank.approved:
                continue
        # Constraints may carry batch approval from UI
        cons = item.constraints if isinstance(item.constraints, dict) else {}
        if cons.get("batch_approved"):
            continue
        return False
    return True


async def evaluate_for_application(
    ctx: WorkspaceContext,
    application_id: uuid.UUID,
    *,
    settings: Settings,
    checkpoint_fired: bool = False,
) -> PolicyVerdict:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    track = await ctx.session.get(Track, app.track_id)
    if track is None:
        raise AppError("not_found", "Track not found", 404)
    job = await ctx.session.get(Job, app.job_id)
    auto = _auto_settings(track)
    ws = await ctx.session.get(Workspace, ctx.workspace_id)
    ws_settings = (ws.settings if ws else None) or {}
    ws_kill = bool((ws_settings.get("auto_submit") or {}).get("kill_switch", False))

    apply_url = app.apply_url or (job.apply_url if job else "") or ""
    ats = detect_ats(apply_url)
    risk = (
        await ctx.session.execute(select(JobRisk).where(JobRisk.job_id == app.job_id))
    ).scalar_one_or_none()
    risk_level = risk.level if risk else "green"

    tj = (
        await ctx.session.execute(
            select(TrackJob).where(
                TrackJob.track_id == app.track_id,
                TrackJob.job_id == app.job_id,
                TrackJob.workspace_id == ctx.workspace_id,
            )
        )
    ).scalar_one_or_none()
    score = (
        float(tj.score * 100)
        if tj and tj.score is not None and tj.score <= 1
        else (float(tj.score) if tj and tj.score is not None else None)
    )

    prefs = await strategy_svc.get_prefs(ctx)
    cap = await caps_mod.check_company_cap(
        ctx,
        company_name=app.company_name,
        company_cap=prefs.company_cap,
        window_days=prefs.company_cap_window_days,
        exclude_application_id=app.id,
    )

    # Daily cap from track settings
    daily_cap = int((track.settings or {}).get("daily_application_cap") or 20)
    since = _now() - timedelta(days=1)
    day_count = int(
        (
            await ctx.session.execute(
                select(func.count())
                .select_from(Application)
                .where(
                    Application.workspace_id == ctx.workspace_id,
                    Application.track_id == track.id,
                    Application.status.in_(("submitted", "in_progress", "needs_you")),
                    Application.created_at >= since,
                )
            )
        ).scalar_one()
        or 0
    )

    fresh = freshness_for(
        job_id=job.id if job else app.job_id,
        posted_at=job.posted_at if job else None,
        first_seen_at=job.first_seen_at if job else None,
    )
    # Auto-submit prefers high/medium freshness (≤72h)
    job_fresh = fresh.boost in {"high", "medium"}

    answers_ok = await _answers_all_approved(ctx, application_id)

    return pol.evaluate(
        autonomy=track.autonomy,
        ats=ats,
        risk_level=risk_level,
        match_score=score,
        score_threshold=auto["score_threshold"],
        answers_all_approved=answers_ok,
        checkpoint_fired=checkpoint_fired,
        company_cap_exceeded=cap.exceeds,
        daily_cap_exceeded=day_count >= daily_cap,
        job_open=bool(job and job.status == "open"),
        job_fresh_enough=job_fresh,
        kill_switch_track=auto["kill_switch"] or auto["anomaly_paused"],
        kill_switch_workspace=ws_kill,
        global_enabled=bool(getattr(settings, "auto_submit_enabled", False)),
        live_enabled=auto["live_enabled"],
        dry_run_remaining=auto["dry_run_remaining"],
    )


async def record_dry_run(
    ctx: WorkspaceContext,
    *,
    track_id: uuid.UUID,
    application_id: uuid.UUID,
    run_id: uuid.UUID | None,
    verdict: PolicyVerdict,
) -> m.AutosubmitDryRun:
    row = m.AutosubmitDryRun(
        workspace_id=ctx.workspace_id,
        track_id=track_id,
        application_id=application_id,
        run_id=run_id,
        would_submit=verdict.dry_run,
        reasons=[r.model_dump() for r in verdict.reasons],
    )
    ctx.session.add(row)
    track = await ctx.session.get(Track, track_id)
    if track:
        auto = _auto_settings(track)
        remaining = max(0, auto["dry_run_remaining"] - 1)
        _write_auto_settings(track, {"dry_run_remaining": remaining})
    await audit.record(
        ctx,
        action="autosubmit.dry_run",
        target_type="application",
        target_id=str(application_id),
        after={"would_submit": verdict.dry_run, "summary": verdict.summary},
        actor_type="system",
    )
    await ctx.session.flush()
    return row


async def list_dry_runs(ctx: WorkspaceContext, track_id: uuid.UUID) -> list[DryRunReportRead]:
    rows = list(
        (
            await ctx.session.execute(
                select(m.AutosubmitDryRun)
                .where(
                    m.AutosubmitDryRun.workspace_id == ctx.workspace_id,
                    m.AutosubmitDryRun.track_id == track_id,
                )
                .order_by(m.AutosubmitDryRun.created_at.desc())
                .limit(50)
            )
        ).scalars()
    )
    return [
        DryRunReportRead(
            id=r.id,
            track_id=r.track_id,
            application_id=r.application_id,
            run_id=r.run_id,
            would_submit=r.would_submit,
            reasons=list(r.reasons or []),
            created_at=r.created_at,
        )
        for r in rows
    ]


async def batch_approve_answers(
    ctx: WorkspaceContext, *, answer_bank_ids: list[uuid.UUID], approved: bool
) -> int:
    n = 0
    for aid in answer_bank_ids:
        row = await ctx.session.get(AnswerBank, aid)
        if row is None or row.workspace_id != ctx.workspace_id:
            continue
        row.approved = approved
        n += 1
    await audit.record(
        ctx,
        action="autosubmit.batch_approve",
        target_type="answer_bank",
        target_id="batch",
        after={"count": n, "approved": approved},
    )
    return n


async def anomaly_status(ctx: WorkspaceContext, track_id: uuid.UUID) -> AnomalyStatusRead:
    track = await ctx.session.get(Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    auto = _auto_settings(track)
    # Failure spike over last 24h among runner applications
    since = _now() - timedelta(hours=24)
    from app.extension import models as ext_m

    total = int(
        (
            await ctx.session.execute(
                select(func.count())
                .select_from(ext_m.ApplyRun)
                .where(
                    ext_m.ApplyRun.workspace_id == ctx.workspace_id,
                    ext_m.ApplyRun.track_id == track_id,
                    ext_m.ApplyRun.created_at >= since,
                )
            )
        ).scalar_one()
        or 0
    )
    failed = int(
        (
            await ctx.session.execute(
                select(func.count())
                .select_from(ext_m.ApplyRun)
                .where(
                    ext_m.ApplyRun.workspace_id == ctx.workspace_id,
                    ext_m.ApplyRun.track_id == track_id,
                    ext_m.ApplyRun.created_at >= since,
                    ext_m.ApplyRun.status == "failed",
                )
            )
        ).scalar_one()
        or 0
    )
    rate = (failed / total) if total else 0.0
    paused = auto["anomaly_paused"]
    reason = auto.get("anomaly_reason")
    if total >= 5 and rate >= 0.5 and not paused:
        _write_auto_settings(
            track,
            {
                "anomaly_paused": True,
                "anomaly_reason": f"Failure rate {rate:.0%} over {total} runs; auto-paused",
                "kill_switch": True,
            },
        )
        paused = True
        reason = f"Failure rate {rate:.0%} over {total} runs; auto-paused"
        await audit.record(
            ctx,
            action="autosubmit.anomaly_pause",
            target_type="track",
            target_id=str(track_id),
            after={"rate": rate, "sample": total},
            actor_type="system",
        )
    return AnomalyStatusRead(
        paused=paused, reason=reason, failure_rate_24h=round(rate, 3), sample_size=total
    )
