"""Minute tick: due schedules → automation chain (idempotent, capped)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mail import Mailer
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext
from app.notifications.digest import send_digests_for_tick
from app.schedules import chain
from app.schedules import cron as cron_util
from app.schedules import service as sched_svc
from app.schedules.models import Schedule
from app.tracks import models as track_models
from app.workspaces.models import WorkspaceMember

logger = logging.getLogger(__name__)


async def _system_ctx(session: AsyncSession, workspace_id: uuid.UUID) -> WorkspaceContext:
    member = (
        await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.is_active.is_(True),
                WorkspaceMember.role.in_(("owner", "admin")),
            )
        )
    ).scalar_one_or_none()
    user_id = member.user_id if member else uuid.UUID(int=0)
    role = member.role if member else "system"
    await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
    return WorkspaceContext(
        session=session,
        user_id=user_id,
        workspace_id=workspace_id,
        role=role,
        request_id=None,
    )


async def tick(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    workspace_id: uuid.UUID | None = None,
    mailer: Mailer | None = None,
) -> dict[str, Any]:
    """Process due schedules once. Missed ticks → fire once (next_run_at advance), not N times."""
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    q = select(Schedule).where(Schedule.enabled.is_(True), Schedule.next_run_at <= now)
    if workspace_id is not None:
        q = q.where(Schedule.workspace_id == workspace_id)
    due = list((await session.execute(q.order_by(Schedule.next_run_at.asc()).limit(50))).scalars())

    fired = 0
    skipped = 0
    details: list[dict[str, Any]] = []

    # Fairness: group by workspace concurrency
    ws_active: dict[uuid.UUID, int] = {}

    for sched in due:
        detail: dict[str, Any] = {"schedule_id": str(sched.id), "track_id": str(sched.track_id)}
        try:
            ctx = await _system_ctx(session, sched.workspace_id)
            track = await session.get(track_models.Track, sched.track_id)
            if track is None or track.status != "active":
                sched.last_skip_reason = "track_inactive"
                sched.next_run_at = cron_util.next_fire(sched.cron, sched.timezone, now)
                skipped += 1
                detail["skip"] = "track_inactive"
                details.append(detail)
                continue

            if cron_util.in_quiet_hours(now, sched.timezone, sched.quiet_hours):
                sched.last_skip_reason = "quiet_hours"
                sched.next_run_at = cron_util.end_of_quiet_hours(
                    now, sched.timezone, sched.quiet_hours or {}
                )
                skipped += 1
                detail["skip"] = "quiet_hours"
                details.append(detail)
                continue

            # Daily cap
            used = await sched_svc.count_runs_today(
                ctx, sched.track_id, tz_name=sched.timezone, now=now
            )
            if used >= sched.daily_cap:
                sched.last_skip_reason = "daily_cap"
                sched.next_run_at = cron_util.next_fire(sched.cron, sched.timezone, now)
                skipped += 1
                detail["skip"] = "daily_cap"
                details.append(detail)
                continue

            # Concurrent per track
            if await chain.has_active_track_run(ctx, sched.track_id):
                sched.last_skip_reason = "previous_run_still_active"
                # Do not advance far; retry next tick
                skipped += 1
                detail["skip"] = "previous_run_still_active"
                details.append(detail)
                continue

            # Workspace concurrency
            active = ws_active.get(sched.workspace_id)
            if active is None:
                active = await chain.active_run_count(ctx)
                ws_active[sched.workspace_id] = active
            if active >= chain.WS_CONCURRENCY_LIMIT:
                sched.last_skip_reason = "workspace_busy"
                skipped += 1
                detail["skip"] = "workspace_busy"
                details.append(detail)
                continue

            # Advance next_run before work (idempotent: one fire per due window)
            sched.next_run_at = cron_util.next_fire(sched.cron, sched.timezone, now)
            sched.last_run_at = now
            sched.last_skip_reason = ""
            await session.flush()

            run = await chain.run_automation_chain(
                ctx,
                sched.track_id,
                trigger="schedule",
                source_id=sched.source_id,
                mailer=mailer,
            )
            ws_active[sched.workspace_id] = ws_active.get(sched.workspace_id, 0) + 1
            fired += 1
            detail["run_id"] = str(run.id)
            detail["status"] = run.status
            details.append(detail)
        except Exception as exc:
            logger.exception("schedule_tick_item_failed id=%s", sched.id)
            sched.last_skip_reason = str(exc)[:200]
            sched.next_run_at = cron_util.next_fire(sched.cron, sched.timezone, now)
            skipped += 1
            detail["skip"] = "error"
            detail["error"] = str(exc)[:120]
            details.append(detail)

    digests = await send_digests_for_tick(
        session, now=now, mailer=mailer, workspace_id=workspace_id
    )
    return {"fired": fired, "skipped": skipped, "digests": digests, "details": details}
