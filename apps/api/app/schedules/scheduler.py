"""Minute scheduler loop: find due schedules for every workspace and run the tick.

The HTTP `POST /schedules/tick` endpoint stays available for tests and manual runs. In deployed
environments this loop drives the same dispatcher once a minute. It is process-local: the API runs
a single uvicorn worker, and the dispatcher advances `next_run_at` before doing work so a duplicate
tick in the same window is a no-op.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.core.rls import set_request_context
from app.schedules.dispatcher import tick

log = logging.getLogger(__name__)


# One advisory lock for the whole tick, so a second API worker skips instead of double-firing.
SCHEDULER_LOCK_KEY = 0x4B414D45  # "KAME"


async def run_once(app: Any, *, now: datetime | None = None) -> dict[str, int]:
    """Tick every live workspace once. Returns fired/skipped totals."""
    now = now or datetime.now(UTC)
    session_factory = app.state.session_factory
    totals = {"fired": 0, "skipped": 0, "workspaces": 0}
    async with session_factory() as lock_session:
        acquired = bool(
            (
                await lock_session.execute(
                    text("SELECT pg_try_advisory_lock(:k)"), {"k": SCHEDULER_LOCK_KEY}
                )
            ).scalar()
        )
        if not acquired:
            log.info("scheduler_tick_skipped_lock")
            totals["skipped_lock"] = 1
            return totals
        try:
            totals = await _tick_all(app, session_factory, now)
        finally:
            await lock_session.execute(
                text("SELECT pg_advisory_unlock(:k)"), {"k": SCHEDULER_LOCK_KEY}
            )
    return totals


async def _tick_all(app: Any, session_factory: Any, now: datetime) -> dict[str, int]:
    totals = {"fired": 0, "skipped": 0, "workspaces": 0}
    async with session_factory() as session:
        ids = [row[0] for row in (await session.execute(text("SELECT scheduler_workspace_ids()")))]

    for wid in ids:
        try:
            async with session_factory() as session, session.begin():
                await set_request_context(session, user_id=None, workspace_id=str(wid))
                result = await tick(
                    session,
                    now=now,
                    workspace_id=wid,
                    mailer=getattr(app.state, "mailer", None),
                )
            totals["fired"] += int(result.get("fired") or 0)
            totals["skipped"] += int(result.get("skipped") or 0)
            totals["workspaces"] += 1
        except Exception:
            log.exception("scheduler_workspace_failed workspace=%s", wid)

    # Recover runs whose runner stopped heartbeating.
    try:
        from app.runs.service import reap_stuck_runs

        totals["reaped"] = await reap_stuck_runs(session_factory, now=now)
    except Exception:
        log.exception("scheduler_reaper_failed")

    # Fail tailor runs whose worker never finished (API restart/crash).
    try:
        from app.applications.service import reap_stale_tailor_runs

        totals["stale_tailor"] = await reap_stale_tailor_runs(session_factory, now=now)
    except Exception:
        log.exception("scheduler_stale_tailor_failed")

    # Fail queued discovery runs whose worker never started (API restart/crash).
    try:
        from app.sources.service import reap_stale_discovery_runs

        totals["stale_discovery"] = await reap_stale_discovery_runs(session_factory, now=now)
    except Exception:
        log.exception("scheduler_stale_discovery_failed")

    # Hard-remove workspaces past the 30-day recovery window once a day.
    if now.hour == 3 and now.minute == 0:
        try:
            from app.workspaces.service import purge_deleted_workspaces

            totals["purged_workspaces"] = await purge_deleted_workspaces(session_factory, now=now)
        except Exception:
            log.exception("scheduler_purge_failed")
    return totals


async def scheduler_loop(app: Any) -> None:
    while True:
        # Align to the next minute boundary so schedules fire close to their slot.
        now = datetime.now(UTC)
        await asyncio.sleep(max(1.0, 60.0 - now.second))
        try:
            result = await run_once(app)
            if result["fired"] or result["skipped"]:
                log.info(
                    "scheduler_tick fired=%s skipped=%s workspaces=%s",
                    result["fired"],
                    result["skipped"],
                    result["workspaces"],
                )
        except Exception:
            log.exception("scheduler_tick_failed")
