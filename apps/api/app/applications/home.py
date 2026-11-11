"""Today / command-center payload."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select

from app.applications import metrics as metrics_svc
from app.applications import status as sm
from app.applications.models import Application, ApplicationReminder
from app.audit.models import ActivityLog
from app.core.security import WorkspaceContext
from app.jobs.models import DiscoveryRun, TrackJob
from app.notifications.needs_you import list_needs_you
from app.schedules.models import Schedule
from app.tracks import models as track_models


async def home_brief(
    ctx: WorkspaceContext,
    *,
    period: str = "week",
    tz_name: str = "UTC",
) -> dict[str, Any]:
    needs = await list_needs_you(ctx, limit=20)
    kpis = await metrics_svc.compute_kpis(ctx, period=period, tz_name=tz_name)

    tracks = list(
        (
            await ctx.session.execute(
                select(track_models.Track)
                .where(
                    track_models.Track.workspace_id == ctx.workspace_id,
                    track_models.Track.status.in_(("active", "paused")),
                )
                .order_by(track_models.Track.sort_order.asc())
            )
        )
        .scalars()
        .all()
    )
    track_cards: list[dict[str, Any]] = []
    for tr in tracks:
        tj_counts = (
            await ctx.session.execute(
                select(TrackJob.status, TrackJob.id).where(
                    TrackJob.track_id == tr.id, TrackJob.workspace_id == ctx.workspace_id
                )
            )
        ).all()
        found = len(tj_counts)
        shortlisted = sum(1 for s, _ in tj_counts if s in {"shortlisted", "applied"})
        apps = list(
            (
                await ctx.session.execute(
                    select(Application).where(
                        Application.track_id == tr.id,
                        Application.workspace_id == ctx.workspace_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        tailored = sum(1 for a in apps if a.tailored or sm.normalize(a.status) != "draft")
        applied = sum(1 for a in apps if a.submitted_at)
        responded = sum(
            1 for a in apps if sm.normalize(a.status) in {"responded", "interview", "offer"}
        )
        interview = sum(1 for a in apps if sm.normalize(a.status) in {"interview", "offer"})

        last_run = (
            await ctx.session.execute(
                select(DiscoveryRun)
                .where(
                    DiscoveryRun.track_id == tr.id,
                    DiscoveryRun.workspace_id == ctx.workspace_id,
                )
                .order_by(desc(DiscoveryRun.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        next_sched = (
            await ctx.session.execute(
                select(Schedule)
                .where(
                    Schedule.track_id == tr.id,
                    Schedule.workspace_id == ctx.workspace_id,
                    Schedule.enabled.is_(True),
                )
                .order_by(Schedule.next_run_at.asc().nulls_last())
                .limit(1)
            )
        ).scalar_one_or_none()

        track_cards.append(
            {
                "id": tr.id,
                "name": tr.name,
                "color_hue": tr.color_hue,
                "autonomy": tr.autonomy,
                "status": tr.status,
                "pipeline": {
                    "found": found,
                    "shortlisted": shortlisted,
                    "tailored": tailored,
                    "applied": applied,
                    "responded": responded,
                    "interview": interview,
                },
                "last_run_at": last_run.finished_at or last_run.started_at if last_run else None,
                "next_run_at": next_sched.next_run_at if next_sched else None,
            }
        )

    activity = list(
        (
            await ctx.session.execute(
                select(ActivityLog)
                .where(ActivityLog.workspace_id == ctx.workspace_id)
                .order_by(desc(ActivityLog.created_at))
                .limit(25)
            )
        )
        .scalars()
        .all()
    )
    feed = [
        {
            "id": str(a.id),
            "action": a.action,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "at": a.created_at,
        }
        for a in activity
    ]

    upcoming_runs = []
    for tr in tracks:
        sched = (
            await ctx.session.execute(
                select(Schedule)
                .where(
                    Schedule.track_id == tr.id,
                    Schedule.enabled.is_(True),
                    Schedule.next_run_at.is_not(None),
                )
                .order_by(Schedule.next_run_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if sched and sched.next_run_at:
            upcoming_runs.append(
                {
                    "track_id": tr.id,
                    "track_name": tr.name,
                    "next_run_at": sched.next_run_at,
                    "preview": f"{sched.preset} · {sched.timezone}",
                }
            )

    reminders = list(
        (
            await ctx.session.execute(
                select(ApplicationReminder, Application)
                .join(Application, Application.id == ApplicationReminder.application_id)
                .where(
                    ApplicationReminder.workspace_id == ctx.workspace_id,
                    ApplicationReminder.done_at.is_(None),
                    ApplicationReminder.due_at <= datetime.now(UTC) + timedelta(days=3),
                )
                .order_by(ApplicationReminder.due_at.asc())
                .limit(10)
            )
        ).all()
    )
    reminder_items = [
        {
            "id": r.id,
            "application_id": app.id,
            "due_at": r.due_at,
            "draft": r.draft,
            "job_title": app.job_title,
            "company_name": app.company_name,
        }
        for r, app in reminders
    ]

    matched = int(kpis["kpis"].get("matched") or 0)
    needs_n = needs["count"]
    if track_cards:
        track_word = "search" if len(track_cards) == 1 else "searches"
        match_word = "match" if matched == 1 else "matches"
        lead = f"{matched} {match_word} across {len(track_cards)} {track_word}."
        if needs_n == 0:
            headline = f"{lead} Nothing needs you."
        elif needs_n == 1:
            headline = f"{lead} 1 thing needs you."
        else:
            headline = f"{lead} {needs_n} things need you."
    elif needs_n == 0:
        headline = "Set up a Track to start finding roles."
    elif needs_n == 1:
        headline = "1 thing needs you."
    else:
        headline = f"{needs_n} things need you."

    empty = len(tracks) == 0

    return {
        "headline": headline,
        "needs_you": needs,
        "kpis": kpis,
        "tracks": track_cards,
        "activity": feed,
        "upcoming_runs": upcoming_runs,
        "reminders": reminder_items,
        "empty": empty,
    }
