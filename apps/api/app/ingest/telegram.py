"""Telegram bot link codes and outbound messages."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from app.core.config import Settings
from app.core.security import WorkspaceContext
from app.ingest.models import TelegramLink

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


async def get_link(ctx: WorkspaceContext) -> TelegramLink | None:
    return (
        await ctx.session.execute(
            select(TelegramLink).where(
                TelegramLink.workspace_id == ctx.workspace_id,
                TelegramLink.user_id == ctx.user_id,
            )
        )
    ).scalar_one_or_none()


async def start_link(ctx: WorkspaceContext, settings: Settings) -> TelegramLink:
    row = await get_link(ctx)
    code = secrets.token_urlsafe(8)
    exp = _now() + timedelta(minutes=15)
    if row is None:
        row = TelegramLink(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            link_code=code,
            code_expires_at=exp,
        )
        ctx.session.add(row)
    else:
        row.link_code = code
        row.code_expires_at = exp
    await ctx.session.flush()
    return row


async def unlink(ctx: WorkspaceContext) -> None:
    row = await get_link(ctx)
    if row is None:
        return
    row.chat_id = None
    row.linked_at = None
    row.link_code = None
    row.code_expires_at = None


async def complete_link_by_code(session, *, code: str, chat_id: str) -> TelegramLink | None:
    from app.core.rls import set_request_context

    row = (
        await session.execute(select(TelegramLink).where(TelegramLink.link_code == code))
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.code_expires_at and row.code_expires_at < _now():
        return None
    # Set workspace so WITH CHECK allows the update.
    await set_request_context(session, user_id=str(row.user_id), workspace_id=str(row.workspace_id))
    row.chat_id = str(chat_id)
    row.linked_at = _now()
    row.link_code = None
    row.code_expires_at = None
    await session.flush()
    return row


async def notify_user(
    ctx: WorkspaceContext,
    *,
    user_id: uuid.UUID,
    text: str,
    settings: Settings,
) -> bool:
    token = getattr(settings, "telegram_bot_token", None)
    if not token:
        return False
    row = (
        await ctx.session.execute(
            select(TelegramLink).where(
                TelegramLink.workspace_id == ctx.workspace_id,
                TelegramLink.user_id == user_id,
                TelegramLink.chat_id.is_not(None),
            )
        )
    ).scalar_one_or_none()
    if row is None or not row.chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                url,
                json={
                    "chat_id": row.chat_id,
                    "text": text[:3500],
                    "disable_web_page_preview": True,
                },
            )
            return r.status_code < 300
    except Exception:
        log.exception("telegram_send_failed")
        return False


async def handle_update(session, settings: Settings, update: dict) -> None:
    """Process Telegram webhook update: /start CODE links the chat."""
    message = update.get("message") or update.get("edited_message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not text or chat_id is None:
        return
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        code = parts[1].strip() if len(parts) > 1 else ""
        if not code:
            return
        await complete_link_by_code(session, code=code, chat_id=str(chat_id))
        token = getattr(settings, "telegram_bot_token", None)
        if token:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "Linked. You will get Needs-you alerts here.",
                        },
                    )
            except Exception:
                log.exception("telegram_ack_failed")
        return
