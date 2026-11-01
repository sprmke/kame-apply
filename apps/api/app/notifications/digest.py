"""Daily digest at 08:00 local: strong matches, needs-you, flags."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.mail import Mail, Mailer
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext
from app.notifications import service as notif
from app.notifications.models import Notification
from app.notifications.needs_you import list_needs_you
from app.workspaces.models import WorkspaceMember

logger = logging.getLogger(__name__)


def _is_digest_hour(now: datetime, tz_name: str) -> bool:
    local = now.astimezone(ZoneInfo(tz_name))
    return local.hour == 8 and local.minute < 2  # within the minute-tick window near 08:00


def render_digest_text(
    *, strong: int, needs: int, flags: int, lines: list[str], auto_submitted: int = 0
) -> str:
    parts = [
        "Kame Apply daily digest",
        "",
        f"Strong matches: {strong}",
        f"Needs you: {needs}",
        f"Risk flags: {flags}",
        f"Auto-submitted (review sample): {auto_submitted}",
        "",
    ]
    parts.extend(lines[:20])
    parts.append("")
    parts.append("Open the app to review. Unsubscribe from Settings → Notifications.")
    return "\n".join(parts)


async def send_digests_for_tick(
    session: AsyncSession,
    *,
    now: datetime,
    mailer: Mailer | None,
    workspace_id: Any | None = None,
) -> int:
    """Send at most one digest per user/workspace per local day. Returns count sent."""
    q = (
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.is_active.is_(True))
    )
    if workspace_id is not None:
        q = q.where(WorkspaceMember.workspace_id == workspace_id)
    rows = (await session.execute(q)).all()
    sent = 0
    for member, user in rows:
        try:
            if not _is_digest_hour(now, user.timezone or "UTC"):
                continue
            await set_request_context(
                session, user_id=str(user.id), workspace_id=str(member.workspace_id)
            )
            ctx = WorkspaceContext(
                session=session,
                user_id=user.id,
                workspace_id=member.workspace_id,
                role=member.role,
                request_id=None,
            )
            if not await notif._pref_enabled(ctx, user_id=user.id, channel="email", event="digest"):
                continue
            if await notif._email_blocked(ctx, user.id):
                continue

            day_key = now.astimezone(ZoneInfo(user.timezone or "UTC")).date().isoformat()
            dedupe = f"digest:{day_key}"
            # Skip if already emitted today (in-app digest marker)
            existing = (
                await session.execute(
                    select(Notification).where(
                        Notification.workspace_id == member.workspace_id,
                        Notification.user_id == user.id,
                        Notification.type == "digest",
                        Notification.dedupe_key == dedupe,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                continue

            needs = await list_needs_you(ctx, limit=20)
            strong = sum(1 for i in needs["items"] if i["kind"] == "tailoring_review")
            flags = sum(1 for i in needs["items"] if i["kind"] == "risk_decision")
            lines = [f"- {i['title']}: {i['detail']}" for i in needs["items"][:10]]
            body = render_digest_text(strong=strong, needs=needs["count"], flags=flags, lines=lines)
            title = f"Digest: {needs['count']} items"
            await notif.emit(
                ctx,
                user_id=user.id,
                event="digest",
                title=title,
                body=body,
                payload={"strong": strong, "needs": needs["count"], "flags": flags},
                dedupe_key=dedupe,
            )
            if mailer and user.email:
                await mailer.send(Mail(to=user.email, subject=title, text=body))
            sent += 1
        except Exception:
            logger.exception("digest_failed user=%s", user.id)
    return sent
