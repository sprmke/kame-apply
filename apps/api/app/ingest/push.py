"""Web Push subscription storage and best-effort send (VAPID)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from pywebpush import WebPushException, webpush
from sqlalchemy import select

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.core.ssrf import is_public_http_url_literal
from app.ingest.models import PushSubscription

log = logging.getLogger(__name__)


def vapid_enabled(settings: Settings) -> bool:
    return bool(
        getattr(settings, "vapid_public_key", None) and getattr(settings, "vapid_private_key", None)
    )


async def upsert_subscription(
    ctx: WorkspaceContext,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str,
) -> PushSubscription:
    row = (
        await ctx.session.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == ctx.user_id,
                PushSubscription.endpoint == endpoint,
            )
        )
    ).scalar_one_or_none()
    if row:
        row.p256dh = p256dh
        row.auth = auth
        row.user_agent = user_agent[:300]
        row.workspace_id = ctx.workspace_id
        return row
    row = PushSubscription(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=user_agent[:300],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def list_subscriptions(ctx: WorkspaceContext) -> list[PushSubscription]:
    return list(
        (
            await ctx.session.execute(
                select(PushSubscription).where(PushSubscription.user_id == ctx.user_id)
            )
        ).scalars()
    )


async def delete_subscription(ctx: WorkspaceContext, sub_id: uuid.UUID) -> None:
    row = await ctx.session.get(PushSubscription, sub_id)
    if row is None or row.user_id != ctx.user_id:
        raise AppError("not_found", "Subscription not found", 404)
    await ctx.session.delete(row)


async def notify_user(
    ctx: WorkspaceContext,
    *,
    user_id: uuid.UUID,
    title: str,
    body: str,
    href: str,
    settings: Settings,
) -> int:
    """Send a real Web Push notification to every subscription for this user."""
    rows = list(
        (
            await ctx.session.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id == user_id,
                    PushSubscription.workspace_id == ctx.workspace_id,
                )
            )
        ).scalars()
    )
    if not rows:
        return 0
    payload = json.dumps({"title": title, "body": body, "href": href})
    sent = 0
    for row in rows:
        # Endpoints are user-supplied; never POST to a private address.
        if not is_public_http_url_literal(row.endpoint):
            log.warning("push_endpoint_blocked")
            continue
        if not settings.vapid_private_key or not settings.vapid_public_key:
            log.warning("push_not_configured")
            return sent
        try:
            await asyncio.to_thread(_send_one, row, payload, settings)
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {404, 410}:
                await ctx.session.delete(row)
            else:
                log.warning("push_send_failed status=%s", status)
        except Exception:
            log.exception("push_send_failed")
    return sent


def _send_one(row: PushSubscription, payload: str, settings: Settings) -> None:
    """Blocking Web Push call (runs in a worker thread)."""
    webpush(
        subscription_info={
            "endpoint": row.endpoint,
            "keys": {"p256dh": row.p256dh, "auth": row.auth},
        },
        data=payload,
        vapid_private_key=settings.vapid_private_key,
        vapid_claims={"sub": settings.vapid_subject},
        timeout=10,
    )
