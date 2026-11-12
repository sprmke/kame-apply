"""Recommended search settings from what actually happened (A8).

Rules only, no LLM. The UI shows the recommendation as a chip with one action. Applying it
goes through the normal track and schedule endpoints, so the change is audited.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.ai.models import AiCredential
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import DiscoveryRun
from app.schedules.models import Schedule
from app.sources.models import TrackSource
from app.tracks.models import Track

DEFAULT_MIN_MATCH = 85


def _preset_for(new_per_day: float) -> str:
    if new_per_day >= 8:
        return "every_4_hours"
    if new_per_day >= 3:
        return "every_2_hours"
    return "daily_morning"


def _cap_for(new_per_day: float) -> int:
    if new_per_day <= 0:
        return 12
    return max(8, min(24, round(new_per_day * 1.5)))


async def recommend(ctx: WorkspaceContext, track_id: uuid.UUID) -> dict[str, Any]:
    track = await ctx.session.get(Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("track_not_found", "Search not found", 404)

    sources = (
        (
            await ctx.session.execute(
                select(TrackSource).where(
                    TrackSource.track_id == track_id,
                    TrackSource.workspace_id == ctx.workspace_id,
                )
            )
        )
        .scalars()
        .all()
    )
    enabled_sources = sum(1 for row in sources if row.enabled)

    since = datetime.now(UTC) - timedelta(days=14)
    runs = (
        (
            await ctx.session.execute(
                select(DiscoveryRun)
                .where(
                    DiscoveryRun.track_id == track_id,
                    DiscoveryRun.workspace_id == ctx.workspace_id,
                    DiscoveryRun.created_at >= since,
                )
                .order_by(DiscoveryRun.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    new_counts = [int((row.progress or {}).get("jobs_new") or 0) for row in runs]
    total_new = sum(new_counts)
    new_per_day = total_new / 14 if total_new else 0.0
    per_run = Counter(new_counts).most_common(1)[0][0] if new_counts else 0

    cred = (
        await ctx.session.execute(
            select(AiCredential.id)
            .where(
                AiCredential.workspace_id == ctx.workspace_id,
                AiCredential.status == "valid",
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    schedule = (
        await ctx.session.execute(
            select(Schedule)
            .where(
                Schedule.track_id == track_id,
                Schedule.workspace_id == ctx.workspace_id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    reasons: list[str] = []
    autonomy = "prepare" if cred else "discover"
    if cred:
        reasons.append("AI is connected, so shortlisted jobs can get a draft.")
    else:
        reasons.append("No AI is connected yet, so we stop after finding and scoring.")

    preset = _preset_for(new_per_day)
    if new_per_day >= 8:
        reasons.append(f"Your searches bring about {round(new_per_day)} new jobs a day.")
    elif new_per_day > 0:
        reasons.append("Your searches bring a few new jobs a day.")
    else:
        reasons.append("No runs yet, so this starts with the usual pace.")

    cap = _cap_for(new_per_day)
    return {
        "autonomy": autonomy,
        "preset": preset,
        "timezone": (schedule.timezone if schedule else "UTC"),
        "quiet_hours": (schedule.quiet_hours if schedule else {"start": "22:00", "end": "07:00"}),
        "daily_cap": cap,
        "minimum_match": DEFAULT_MIN_MATCH,
        "sources": enabled_sources,
        "new_per_day": round(new_per_day, 1),
        "per_run": per_run,
        "reasons": reasons[:3],
    }
