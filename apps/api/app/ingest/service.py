"""Inbound address lifecycle, email webhook processing, job upsert."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.audit import service as audit
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.ingest import models as m
from app.ingest.parsers import jobs_to_dicts, parse_mime
from app.jobs.ingest import upsert_raw_job
from app.notifications import service as notif
from app.sources.models import Source
from kame_core.sources.base import RawJob

log = logging.getLogger(__name__)

SETUP_GUIDES = [
    {
        "provider": "gmail",
        "title": "Gmail auto-forward",
        "steps": [
            "Open Gmail Settings → Filters and blocked addresses → Create a new filter.",
            "From: linkedin.com OR indeed.com OR jobstreet.com OR glassdoor.com OR kalibrr.com",
            "Create filter → Forward it to your Kame address (confirm the first mail).",
        ],
    },
    {
        "provider": "outlook",
        "title": "Outlook rule",
        "steps": [
            "Settings → Mail → Rules → Add new rule.",
            "Condition: sender contains linkedin.com / indeed.com / jobstreet.com.",
            "Action: Forward to your Kame address.",
        ],
    },
    {
        "provider": "linkedin",
        "title": "LinkedIn job alerts",
        "steps": [
            "On LinkedIn, save a search and turn on email alerts.",
            "Forward those emails to your Kame address (or use the Gmail filter).",
        ],
    },
]


def _now() -> datetime:
    return datetime.now(UTC)


def new_inbound_token() -> str:
    return secrets.token_urlsafe(18)


def format_address(token: str, settings: Settings) -> str:
    domain = getattr(settings, "inbound_email_domain", None) or "in.kameapply.local"
    return f"alerts+{token}@{domain}"


def verify_webhook_signature(settings: Settings, *, body: bytes, signature: str | None) -> bool:
    secret = getattr(settings, "inbound_webhook_secret", None) or ""
    if not secret:
        # Local/test: allow when secret unset
        return settings.environment in {"local", "test", "dev"}
    if not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    got = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, got)


async def get_or_create_address(ctx: WorkspaceContext, settings: Settings) -> m.InboundAddress:
    row = (
        await ctx.session.execute(
            select(m.InboundAddress).where(m.InboundAddress.workspace_id == ctx.workspace_id)
        )
    ).scalar_one_or_none()
    if row:
        if row.notify_user_id is None:
            row.notify_user_id = ctx.user_id
        return row
    row = m.InboundAddress(
        workspace_id=ctx.workspace_id,
        token=new_inbound_token(),
        enabled=True,
        notify_user_id=ctx.user_id,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="inbound.address_created",
        target_type="inbound_address",
        target_id=str(row.id),
    )
    return row


async def rotate_address(ctx: WorkspaceContext, settings: Settings) -> m.InboundAddress:
    row = await get_or_create_address(ctx, settings)
    row.token = new_inbound_token()
    row.rotated_at = _now()
    await audit.record(
        ctx,
        action="inbound.address_rotated",
        target_type="inbound_address",
        target_id=str(row.id),
    )
    return row


async def list_messages(ctx: WorkspaceContext, *, limit: int = 30) -> list[m.InboundMessage]:
    return list(
        (
            await ctx.session.execute(
                select(m.InboundMessage)
                .where(m.InboundMessage.workspace_id == ctx.workspace_id)
                .order_by(m.InboundMessage.created_at.desc())
                .limit(limit)
            )
        ).scalars()
    )


async def _ensure_email_source(ctx: WorkspaceContext) -> Source:
    src = (
        await ctx.session.execute(select(Source).where(Source.key == "email_alert"))
    ).scalar_one_or_none()
    if src:
        return src
    src = Source(
        key="email_alert",
        name="Email alerts",
        kind="email",
        adapter="email_alert",
        terms_note="User-forwarded job alert emails",
        enabled_global=True,
    )
    ctx.session.add(src)
    await ctx.session.flush()
    return src


async def resolve_workspace_by_token(session, token: str) -> m.InboundAddress | None:
    return (
        await session.execute(
            select(m.InboundAddress).where(
                m.InboundAddress.token == token, m.InboundAddress.enabled.is_(True)
            )
        )
    ).scalar_one_or_none()


async def process_inbound_email(
    ctx: WorkspaceContext,
    *,
    raw: bytes,
    sender: str,
    subject: str,
    settings: Settings,
    storage: Any | None = None,
) -> m.InboundMessage:
    # Rate limit: max 60 messages / hour / workspace
    since = _now() - timedelta(hours=1)
    recent = (
        await ctx.session.execute(
            select(m.InboundMessage.id).where(
                m.InboundMessage.workspace_id == ctx.workspace_id,
                m.InboundMessage.created_at >= since,
            )
        )
    ).all()
    if len(recent) >= 60:
        raise AppError("rate_limited", "Too many inbound emails", 429)

    msg = m.InboundMessage(
        workspace_id=ctx.workspace_id,
        sender=sender[:500],
        subject=subject[:500],
        status="received",
    )
    ctx.session.add(msg)
    await ctx.session.flush()

    r2_key = None
    if storage is not None:
        try:
            r2_key = f"ws/{ctx.workspace_id}/inbound/{msg.id}.eml"
            await storage.put(r2_key, raw, "message/rfc822")
            msg.r2_raw = r2_key
        except Exception:
            log.exception("inbound_r2_failed")

    result = parse_mime(raw, sender=sender, subject=subject)
    msg.provider = result.provider
    msg.confidence = result.confidence
    msg.parsed = jobs_to_dicts(result.jobs)

    if result.kind == "forward_confirm":
        msg.status = "needs_review"
        await notif.emit(
            ctx,
            user_id=ctx.user_id,
            event="needs_review",
            title="Confirm email forwarding",
            body=subject[:120] or "Open the confirmation link in the forwarded mail",
            payload={"inbound_message_id": str(msg.id), "href": "/settings/alerts"},
            dedupe_key=f"forward_confirm:{msg.id}",
        )
        await audit.record(
            ctx,
            action="inbound.forward_confirm",
            target_type="inbound_message",
            target_id=str(msg.id),
            actor_type="system",
        )
        return msg

    if not result.jobs:
        msg.status = "ignored" if result.confidence == 0 else "needs_review"
        if msg.status == "needs_review":
            await notif.emit(
                ctx,
                user_id=ctx.user_id,
                event="needs_review",
                title="Review imported jobs",
                body=subject[:120] or "Could not parse alert confidently",
                payload={"inbound_message_id": str(msg.id), "href": "/settings/alerts"},
                dedupe_key=f"inbound_review:{msg.id}",
            )
        return msg

    await _ensure_email_source(ctx)
    created = 0
    low = result.confidence < 0.6
    for job in result.jobs:
        raw_job = RawJob(
            external_id=hashlib.sha256(job.url.encode()).hexdigest()[:24],
            source_key="email_alert",
            title=job.title,
            company_name=job.company,
            url=job.url,
            apply_url=job.url,
            location_text=job.location,
            description_text=f"Imported from {result.provider} alert",
            raw={"provider": result.provider, "inbound_message_id": str(msg.id)},
        )
        try:
            _job, is_new = await upsert_raw_job(ctx.session, raw_job)
            if is_new:
                created += 1
        except Exception:
            log.exception("inbound_job_upsert_failed")
    msg.jobs_created = created
    msg.status = "needs_review" if low else "parsed"
    if low:
        await notif.emit(
            ctx,
            user_id=ctx.user_id,
            event="needs_review",
            title="Review imported jobs",
            body=f"{len(result.jobs)} jobs from {result.provider}",
            payload={"inbound_message_id": str(msg.id), "href": "/settings/alerts"},
            dedupe_key=f"inbound_review:{msg.id}",
        )
    await audit.record(
        ctx,
        action="inbound.parsed",
        target_type="inbound_message",
        target_id=str(msg.id),
        after={"provider": result.provider, "jobs": len(result.jobs), "created": created},
        actor_type="system",
    )
    # Push / Telegram for strong imports
    if created and not low:
        from app.ingest import push as push_svc
        from app.ingest import telegram as tg_svc

        title = f"{created} jobs from {result.provider}"
        await push_svc.notify_user(
            ctx,
            user_id=ctx.user_id,
            title=title,
            body=subject[:120],
            href="/jobs",
            settings=settings,
        )
        await tg_svc.notify_user(
            ctx,
            user_id=ctx.user_id,
            text=f"{title}\n{settings.web_base_url.rstrip('/')}/jobs",
            settings=settings,
        )
    return msg
