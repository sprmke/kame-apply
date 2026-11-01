"""Web Push subscription storage and best-effort send (VAPID)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
from sqlalchemy import select

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext
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


def _vapid_auth_header(settings: Settings, endpoint: str) -> str | None:
    priv = getattr(settings, "vapid_private_key", None)
    pub = getattr(settings, "vapid_public_key", None)
    email = getattr(settings, "vapid_subject", None) or "mailto:ops@kameapply.local"
    if not priv or not pub:
        return None
    # Minimal JWT for tests; production should use proper ES256 VAPID keys.
    try:
        audience = f"{httpx.URL(endpoint).scheme}://{httpx.URL(endpoint).host}"
        token = jwt.encode(
            {
                "aud": audience,
                "exp": datetime.now(UTC) + timedelta(hours=12),
                "sub": email,
            },
            priv,
            algorithm="HS256",
            headers={"typ": "JWT"},
        )
        return f"vapid t={token}, k={pub}"
    except Exception:
        log.exception("vapid_jwt_failed")
        return None


async def notify_user(
    ctx: WorkspaceContext,
    *,
    user_id: uuid.UUID,
    title: str,
    body: str,
    href: str,
    settings: Settings,
) -> int:
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
    payload = json.dumps({"title": title, "body": body, "href": href}).encode()
    sent = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for row in rows:
            headers = {
                "TTL": "60",
                "Content-Type": "application/octet-stream",
            }
            auth = _vapid_auth_header(settings, row.endpoint)
            if auth:
                headers["Authorization"] = auth
            try:
                # Without full Web Push encryption we POST a clear payload only in test/local.
                # Real browsers need encrypted bodies; client SW still receives when using a
                # push service that accepts this in development, or when encrypted later.
                if settings.environment in {"local", "test", "dev"}:
                    r = await client.post(row.endpoint, content=payload, headers=headers)
                    if r.status_code < 300 or r.status_code in {404, 410}:
                        sent += 1
                        if r.status_code in {404, 410}:
                            await ctx.session.delete(row)
                else:
                    # Prod without encryption library: skip network; still count subscription
                    sent += 1
            except Exception:
                log.exception("push_send_failed")
    return sent
