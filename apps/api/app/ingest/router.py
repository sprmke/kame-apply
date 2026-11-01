"""HTTP: inbound alerts settings, webhook, push, Telegram."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext, get_db, require_action
from app.ingest import push as push_svc
from app.ingest import schemas as s
from app.ingest import service
from app.ingest import telegram as tg_svc

router = APIRouter(tags=["ingest"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))
Manage = Depends(require_action("workspace.update"))


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.get("/inbound/address", response_model=s.InboundAddressRead)
async def get_address(request: Request, ctx: WorkspaceContext = Manage):
    settings = _settings(request)
    row = await service.get_or_create_address(ctx, settings)
    return s.InboundAddressRead(
        id=row.id,
        address=service.format_address(row.token, settings),
        enabled=row.enabled,
        created_at=row.created_at,
        rotated_at=row.rotated_at,
    )


@router.post("/inbound/address/rotate", response_model=s.InboundAddressRead)
async def rotate_address(request: Request, ctx: WorkspaceContext = Manage):
    settings = _settings(request)
    row = await service.rotate_address(ctx, settings)
    return s.InboundAddressRead(
        id=row.id,
        address=service.format_address(row.token, settings),
        enabled=row.enabled,
        created_at=row.created_at,
        rotated_at=row.rotated_at,
    )


@router.get("/inbound/guides", response_model=list[s.SetupGuideRead])
async def guides(ctx: WorkspaceContext = Read):
    return [s.SetupGuideRead(**g) for g in service.SETUP_GUIDES]


@router.get("/inbound/messages", response_model=list[s.InboundMessageRead])
async def messages(ctx: WorkspaceContext = Read):
    rows = await service.list_messages(ctx)
    return [
        s.InboundMessageRead(
            id=r.id,
            sender=r.sender,
            subject=r.subject,
            provider=r.provider,
            status=r.status,
            confidence=r.confidence,
            jobs_created=r.jobs_created,
            parsed=list(r.parsed or []),
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/webhooks/inbound-email", response_model=s.WebhookAck)
async def inbound_email_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
    x_kame_signature: str | None = Header(default=None),
    x_inbound_token: str | None = Header(default=None),
):
    """Cloudflare Email Worker → signed webhook. Body = raw MIME; token in header or query."""
    settings = _settings(request)
    body = await request.body()
    if not service.verify_webhook_signature(settings, body=body, signature=x_kame_signature):
        raise AppError("unauthenticated", "Authentication required", 401)

    token = x_inbound_token or request.query_params.get("token") or ""
    if not token:
        # Also accept To: alerts+TOKEN@domain in JSON envelope
        try:
            import json

            envelope = json.loads(body)
            token = str(envelope.get("token") or "")
            raw_b64 = envelope.get("raw_b64")
            if raw_b64:
                import base64

                body = base64.b64decode(raw_b64)
            sender = str(envelope.get("from") or "")
            subject = str(envelope.get("subject") or "")
        except Exception:
            sender, subject = "", ""
            raise AppError("bad_request", "Missing inbound token", 400) from None
    else:
        sender = request.query_params.get("from") or ""
        subject = request.query_params.get("subject") or ""

    # Lookup without workspace RLS first (token is the secret)
    await set_request_context(session, user_id=None, workspace_id=None)
    addr = await service.resolve_workspace_by_token(session, token)
    if addr is None:
        raise AppError("not_found", "Unknown inbound address", 404)
    if addr.notify_user_id is None:
        raise AppError("not_found", "Workspace not found", 404)

    await set_request_context(
        session,
        user_id=str(addr.notify_user_id),
        workspace_id=str(addr.workspace_id),
    )
    ctx = WorkspaceContext(
        session=session,
        user_id=addr.notify_user_id,
        workspace_id=addr.workspace_id,
        role="owner",
        request_id=getattr(request.state, "request_id", None),
    )
    storage = getattr(request.app.state, "storage", None)
    msg = await service.process_inbound_email(
        ctx,
        raw=body,
        sender=sender,
        subject=subject,
        settings=settings,
        storage=storage,
    )
    await session.commit()
    return s.WebhookAck(
        ok=True,
        message_id=msg.id,
        status=msg.status,
        jobs_created=msg.jobs_created,
    )


@router.get("/push/vapid-public", response_model=s.VapidPublicRead)
async def vapid_public(request: Request, ctx: WorkspaceContext = Read):
    settings = _settings(request)
    key = getattr(settings, "vapid_public_key", None) or ""
    return s.VapidPublicRead(public_key=key, enabled=bool(key))


@router.post("/push/subscriptions", response_model=s.PushSubscriptionRead, status_code=201)
async def subscribe_push(body: s.PushSubscribeBody, ctx: WorkspaceContext = Write):
    row = await push_svc.upsert_subscription(
        ctx,
        endpoint=body.endpoint,
        p256dh=body.p256dh,
        auth=body.auth,
        user_agent=body.user_agent,
    )
    return s.PushSubscriptionRead(id=row.id, endpoint=row.endpoint, created_at=row.created_at)


@router.get("/push/subscriptions", response_model=list[s.PushSubscriptionRead])
async def list_push(ctx: WorkspaceContext = Read):
    return [
        s.PushSubscriptionRead(id=r.id, endpoint=r.endpoint, created_at=r.created_at)
        for r in await push_svc.list_subscriptions(ctx)
    ]


@router.delete("/push/subscriptions/{sub_id}", response_model=s.OkRead)
async def delete_push(sub_id: uuid.UUID, ctx: WorkspaceContext = Write):
    await push_svc.delete_subscription(ctx, sub_id)
    return s.OkRead()


@router.get("/telegram/link", response_model=s.TelegramLinkRead)
async def telegram_status(request: Request, ctx: WorkspaceContext = Read):
    settings = _settings(request)
    row = await tg_svc.get_link(ctx)
    bot = getattr(settings, "telegram_bot_username", None)
    if row is None:
        return s.TelegramLinkRead(linked=False, bot_username=bot)
    return s.TelegramLinkRead(
        linked=bool(row.chat_id),
        chat_id=row.chat_id,
        link_code=row.link_code,
        code_expires_at=row.code_expires_at,
        bot_username=bot,
    )


@router.post("/telegram/link", response_model=s.TelegramLinkRead)
async def telegram_start(request: Request, ctx: WorkspaceContext = Write):
    settings = _settings(request)
    row = await tg_svc.start_link(ctx, settings)
    return s.TelegramLinkRead(
        linked=bool(row.chat_id),
        chat_id=row.chat_id,
        link_code=row.link_code,
        code_expires_at=row.code_expires_at,
        bot_username=getattr(settings, "telegram_bot_username", None),
    )


@router.post("/telegram/unlink", response_model=s.OkRead)
async def telegram_unlink(ctx: WorkspaceContext = Write):
    await tg_svc.unlink(ctx)
    return s.OkRead()


@router.post("/webhooks/telegram", response_model=s.OkRead)
async def telegram_webhook(request: Request, session: AsyncSession = Depends(get_db)):
    settings = _settings(request)
    secret = getattr(settings, "telegram_webhook_secret", None)
    if secret:
        got = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if got != secret:
            raise AppError("unauthenticated", "Authentication required", 401)
    update = await request.json()
    await set_request_context(session, user_id=None, workspace_id=None)
    await tg_svc.handle_update(session, settings, update)
    await session.commit()
    return s.OkRead()
