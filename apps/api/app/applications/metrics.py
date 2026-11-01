"""KPI + funnel + outcome analytics for the command center."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.applications import status as sm
from app.applications.models import Application
from app.core.security import WorkspaceContext
from app.jobs.models import TrackJob


def _period_start(period: str, *, tz_name: str, now: datetime | None = None) -> datetime | None:
    now = now or datetime.now(UTC)
    z = ZoneInfo(tz_name)
    local = now.astimezone(z)
    if period == "today":
        start = datetime.combine(local.date(), datetime.min.time(), tzinfo=z)
        return start.astimezone(UTC)
    if period == "week":
        start_day = local.date() - timedelta(days=local.weekday())
        start = datetime.combine(start_day, datetime.min.time(), tzinfo=z)
        return start.astimezone(UTC)
    return None  # total


async def compute_kpis(
    ctx: WorkspaceContext,
    *,
    period: str = "week",
    track_id: uuid.UUID | None = None,
    tz_name: str = "UTC",
) -> dict[str, Any]:
    start = _period_start(period, tz_name=tz_name)

    tj_filters = [TrackJob.workspace_id == ctx.workspace_id]
    app_filters = [Application.workspace_id == ctx.workspace_id]
    if track_id:
        tj_filters.append(TrackJob.track_id == track_id)
        app_filters.append(Application.track_id == track_id)
    if start:
        tj_filters.append(TrackJob.created_at >= start)
        # for submitted counts use submitted_at
        pass

    discovered = int(
        (
            await ctx.session.execute(select(func.count()).select_from(TrackJob).where(*tj_filters))
        ).scalar_one()
    )
    matched = int(
        (
            await ctx.session.execute(
                select(func.count())
                .select_from(TrackJob)
                .where(*tj_filters, TrackJob.score.is_not(None), TrackJob.score >= 0.5)
            )
        ).scalar_one()
    )
    shortlisted = int(
        (
            await ctx.session.execute(
                select(func.count())
                .select_from(TrackJob)
                .where(*tj_filters, TrackJob.status.in_(("shortlisted", "applied")))
            )
        ).scalar_one()
    )

    apps_q = select(Application).where(*app_filters)
    apps = list((await ctx.session.execute(apps_q)).scalars().all())
    if start:
        submitted_apps = [
            a
            for a in apps
            if a.submitted_at and a.submitted_at >= start and sm.normalize(a.status) != "withdrawn"
        ]
    else:
        submitted_apps = [a for a in apps if a.submitted_at]

    submitted = len(submitted_apps)
    responded = sum(
        1
        for a in submitted_apps
        if sm.normalize(a.status) in {"responded", "interview", "offer"} or a.responded_at
    )
    interviews = sum(
        1
        for a in submitted_apps
        if sm.normalize(a.status) in {"interview", "offer"} or a.interview_at
    )
    offers = sum(1 for a in submitted_apps if sm.normalize(a.status) == "offer")
    rejected = sum(1 for a in submitted_apps if sm.normalize(a.status) == "rejected")

    response_rate = (responded / submitted) if submitted else 0.0
    interview_rate = (interviews / submitted) if submitted else 0.0

    # Outcome analytics breakdowns
    by_method: dict[str, dict[str, int]] = {}
    by_tailored: dict[str, dict[str, int]] = {"tailored": {}, "base": {}}
    for a in submitted_apps:
        m = a.method or "manual"
        by_method.setdefault(m, {"submitted": 0, "responded": 0, "interview": 0})
        by_method[m]["submitted"] += 1
        st = sm.normalize(a.status)
        if st in {"responded", "interview", "offer"} or a.responded_at:
            by_method[m]["responded"] += 1
        if st in {"interview", "offer"} or a.interview_at:
            by_method[m]["interview"] += 1
        key = "tailored" if a.tailored else "base"
        by_tailored[key].setdefault("submitted", 0)
        by_tailored[key]["submitted"] += 1
        if st in {"responded", "interview", "offer"} or a.responded_at:
            by_tailored[key].setdefault("responded", 0)
            by_tailored[key]["responded"] += 1

    funnel = {
        "discovered": discovered,
        "matched": matched,
        "shortlisted": shortlisted,
        "submitted": submitted,
        "responded": responded,
        "interview": interviews,
        "offer": offers,
        "rejected": rejected,
    }

    return {
        "period": period,
        "track_id": track_id,
        "kpis": {
            "discovered": discovered,
            "matched": matched,
            "shortlisted": shortlisted,
            "submitted": submitted,
            "response_rate": round(response_rate, 4),
            "interview_rate": round(interview_rate, 4),
            "responded": responded,
            "interviews": interviews,
            "offers": offers,
        },
        "funnel": funnel,
        "outcomes": {
            "by_method": by_method,
            "by_tailored": by_tailored,
        },
        "as_of": datetime.now(UTC),
        "day": date.today().isoformat(),
    }
