"""Per-company application caps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.applications.models import Application
from app.core.security import WorkspaceContext
from app.strategy.schemas import CapCheckRead

DEFAULT_CAP = 3
DEFAULT_WINDOW_DAYS = 90
ACTIVE_STATUSES = (
    "ready",
    "in_progress",
    "needs_you",
    "submitted",
    "interview",
    "offer",
)


def prefs_from_settings(settings: dict | None) -> tuple[int, int]:
    s = settings or {}
    cap = int(s.get("company_cap") or DEFAULT_CAP)
    window = int(s.get("company_cap_window_days") or DEFAULT_WINDOW_DAYS)
    return max(1, min(cap, 20)), max(7, min(window, 365))


async def count_active_for_company(
    ctx: WorkspaceContext,
    *,
    company_name: str,
    window_days: int,
    exclude_application_id: uuid.UUID | None = None,
) -> int:
    since = datetime.now(UTC) - timedelta(days=window_days)
    name = (company_name or "").strip().lower()
    q = (
        select(func.count())
        .select_from(Application)
        .where(
            Application.workspace_id == ctx.workspace_id,
            func.lower(Application.company_name) == name,
            Application.status.in_(ACTIVE_STATUSES),
            Application.created_at >= since,
        )
    )
    if exclude_application_id:
        q = q.where(Application.id != exclude_application_id)
    return int((await ctx.session.execute(q)).scalar_one() or 0)


async def check_company_cap(
    ctx: WorkspaceContext,
    *,
    company_name: str,
    company_cap: int = DEFAULT_CAP,
    window_days: int = DEFAULT_WINDOW_DAYS,
    exclude_application_id: uuid.UUID | None = None,
) -> CapCheckRead:
    count = await count_active_for_company(
        ctx,
        company_name=company_name,
        window_days=window_days,
        exclude_application_id=exclude_application_id,
    )
    exceeds = count >= company_cap
    warn = count >= max(1, company_cap - 1)
    if exceeds:
        msg = (
            f"You already have {count} active applications at {company_name} "
            f"in the last {window_days} days (cap {company_cap})."
        )
    elif warn:
        msg = (
            f"{count} of {company_cap} applications used at {company_name} "
            f"in the last {window_days} days."
        )
    else:
        msg = f"{count} of {company_cap} applications used at {company_name}."
    return CapCheckRead(
        company_name=company_name,
        active_count=count,
        cap=company_cap,
        window_days=window_days,
        exceeds=exceeds,
        warn=warn,
        message=msg,
    )
