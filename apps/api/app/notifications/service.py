"""Emit, list, mark-read notifications; preference matrix."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.audit import service as audit
from app.auth.models import User
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.mail import Mail, Mailer
from app.core.security import WorkspaceContext
from app.notifications.models import EmailUnsubscribe, Notification, NotificationPref
from app.notifications.schemas import CHANNELS, EVENTS
from app.workspaces.models import WorkspaceMember

logger = logging.getLogger(__name__)

# Defaults: digest email on; instant email only for needs-you-class events; in-app on for all.
_DEFAULT_EMAIL_ON = {"needs_review", "risk_flag", "run_failed", "budget_reached", "digest"}


def default_enabled(channel: str, event: str) -> bool:
    if channel == "in_app":
        return True
    if channel == "email":
        return event in _DEFAULT_EMAIL_ON
    if channel in {"push", "telegram"}:
        return event in {"needs_review", "risk_flag", "run_failed", "strong_match"}
    return False


async def _pref_enabled(
    ctx: WorkspaceContext, *, user_id: uuid.UUID, channel: str, event: str
) -> bool:
    row = (
        await ctx.session.execute(
            select(NotificationPref).where(
                NotificationPref.workspace_id == ctx.workspace_id,
                NotificationPref.user_id == user_id,
                NotificationPref.channel == channel,
                NotificationPref.event == event,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return default_enabled(channel, event)
    return bool(row.enabled)


async def _email_blocked(ctx: WorkspaceContext, user_id: uuid.UUID) -> bool:
    row = (
        await ctx.session.execute(
            select(EmailUnsubscribe).where(
                EmailUnsubscribe.workspace_id == ctx.workspace_id,
                EmailUnsubscribe.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return row is not None


async def emit(
    ctx: WorkspaceContext,
    *,
    user_id: uuid.UUID,
    event: str,
    title: str,
    body: str = "",
    payload: dict[str, Any] | None = None,
    dedupe_key: str,
    mailer: Mailer | None = None,
) -> Notification | None:
    """Create an in-app notification (and optional instant email). Never raises to callers."""
    try:
        if not await _pref_enabled(ctx, user_id=user_id, channel="in_app", event=event):
            in_app = False
        else:
            in_app = True

        row: Notification | None = None
        if in_app:
            stmt = (
                pg_insert(Notification)
                .values(
                    workspace_id=ctx.workspace_id,
                    user_id=user_id,
                    type=event,
                    title=title[:200],
                    body=body,
                    payload=payload or {},
                    dedupe_key=dedupe_key[:200],
                )
                .on_conflict_do_nothing(
                    constraint="uq_notifications_dedupe",
                )
                .returning(Notification)
            )
            row = (await ctx.session.execute(stmt)).scalar_one_or_none()
            await ctx.session.flush()

        if mailer and await _pref_enabled(ctx, user_id=user_id, channel="email", event=event):
            if event != "digest" and not await _email_blocked(ctx, user_id):
                # Instant email only for needs-you class events.
                if event in ("needs_review", "risk_flag", "run_failed", "budget_reached"):
                    user = await ctx.session.get(User, user_id)
                    if user and user.email:
                        await mailer.send(
                            Mail(to=user.email, subject=title[:120], text=body or title)
                        )

        # Phone and Telegram alerts for Needs-you class events (Phase 17).
        settings = get_settings()
        if event in ("needs_review", "risk_flag", "run_failed", "budget_reached"):
            href = str((payload or {}).get("href") or "/notifications")
            if await _pref_enabled(ctx, user_id=user_id, channel="push", event=event):
                from app.ingest import push as push_svc

                await push_svc.notify_user(
                    ctx,
                    user_id=user_id,
                    title=title,
                    body=body,
                    href=href,
                    settings=settings,
                )
            if await _pref_enabled(ctx, user_id=user_id, channel="telegram", event=event):
                from app.ingest import telegram as tg_svc

                await tg_svc.notify_user(
                    ctx,
                    user_id=user_id,
                    text=f"{title}\n{body}".strip(),
                    settings=settings,
                )

        return row
    except Exception:
        logger.exception("notification_emit_failed event=%s", event)
        return None


async def emit_to_workspace_members(
    ctx: WorkspaceContext,
    *,
    event: str,
    title: str,
    body: str = "",
    payload: dict[str, Any] | None = None,
    dedupe_key: str,
    mailer: Mailer | None = None,
) -> int:
    members = (
        (
            await ctx.session.execute(
                select(WorkspaceMember.user_id).where(
                    WorkspaceMember.workspace_id == ctx.workspace_id,
                    WorkspaceMember.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    n = 0
    for uid in members:
        row = await emit(
            ctx,
            user_id=uid,
            event=event,
            title=title,
            body=body,
            payload=payload,
            dedupe_key=f"{dedupe_key}:{uid}",
            mailer=mailer,
        )
        if row:
            n += 1
    return n


async def list_notifications(
    ctx: WorkspaceContext, *, unread_only: bool = False, limit: int = 50
) -> list[Notification]:
    q = (
        select(Notification)
        .where(
            Notification.workspace_id == ctx.workspace_id,
            Notification.user_id == ctx.user_id,
        )
        .order_by(Notification.created_at.desc())
        .limit(min(limit, 100))
    )
    if unread_only:
        q = q.where(Notification.read_at.is_(None))
    return list((await ctx.session.execute(q)).scalars().all())


async def unread_count(ctx: WorkspaceContext) -> int:
    rows = await list_notifications(ctx, unread_only=True, limit=100)
    return len(rows)


async def mark_read(ctx: WorkspaceContext, notification_id: uuid.UUID) -> Notification:
    row = await ctx.session.get(Notification, notification_id)
    if row is None or row.workspace_id != ctx.workspace_id or row.user_id != ctx.user_id:
        raise AppError("not_found", "Notification not found", 404)
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        await audit.record(
            ctx,
            action="notification.read",
            target_type="notification",
            target_id=str(row.id),
        )
    return row


async def mark_all_read(ctx: WorkspaceContext) -> int:
    result = await ctx.session.execute(
        update(Notification)
        .where(
            Notification.workspace_id == ctx.workspace_id,
            Notification.user_id == ctx.user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    count = int(getattr(result, "rowcount", 0) or 0)
    await audit.record(
        ctx,
        action="notification.read_all",
        target_type="notification",
        after={"count": count},
    )
    return count


async def get_prefs_matrix(ctx: WorkspaceContext) -> list[dict[str, Any]]:
    rows = (
        (
            await ctx.session.execute(
                select(NotificationPref).where(
                    NotificationPref.workspace_id == ctx.workspace_id,
                    NotificationPref.user_id == ctx.user_id,
                )
            )
        )
        .scalars()
        .all()
    )
    by_key = {(r.channel, r.event): r.enabled for r in rows}
    cells = []
    for channel in CHANNELS:
        for event in EVENTS:
            cells.append(
                {
                    "channel": channel,
                    "event": event,
                    "enabled": by_key.get((channel, event), default_enabled(channel, event)),
                }
            )
    return cells


async def upsert_prefs(ctx: WorkspaceContext, cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for cell in cells:
        channel = cell["channel"]
        event = cell["event"]
        enabled = bool(cell["enabled"])
        if channel not in CHANNELS or event not in EVENTS:
            raise AppError("validation_error", "Unknown channel or event", 422)
        stmt = (
            pg_insert(NotificationPref)
            .values(
                workspace_id=ctx.workspace_id,
                user_id=ctx.user_id,
                channel=channel,
                event=event,
                enabled=enabled,
            )
            .on_conflict_do_update(
                constraint="uq_notification_prefs",
                set_={"enabled": enabled, "updated_at": datetime.now(UTC)},
            )
        )
        await ctx.session.execute(stmt)
    await audit.record(
        ctx,
        action="notification.prefs_updated",
        target_type="notification_prefs",
        after={"count": len(cells)},
    )
    return await get_prefs_matrix(ctx)


async def unsubscribe_email(ctx: WorkspaceContext) -> None:
    stmt = (
        pg_insert(EmailUnsubscribe)
        .values(workspace_id=ctx.workspace_id, user_id=ctx.user_id)
        .on_conflict_do_nothing(constraint="uq_email_unsubscribes")
    )
    await ctx.session.execute(stmt)
    # Disable all email prefs
    for event in EVENTS:
        await upsert_prefs(ctx, [{"channel": "email", "event": event, "enabled": False}])
    await audit.record(
        ctx,
        action="notification.email_unsubscribed",
        target_type="email_unsubscribe",
        target_id=str(ctx.user_id),
    )
