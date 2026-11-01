"""HTTP: notification center, prefs, needs-you, SSE, unsubscribe."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.security import WorkspaceContext, require_action
from app.notifications import schemas as s
from app.notifications import service
from app.notifications.needs_you import list_needs_you

router = APIRouter(tags=["notifications"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.get("/notifications", response_model=list[s.NotificationRead])
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    ctx: WorkspaceContext = Read,
):
    return await service.list_notifications(ctx, unread_only=unread_only, limit=limit)


@router.get("/notifications/unread-count")
async def unread_count(ctx: WorkspaceContext = Read):
    return {"count": await service.unread_count(ctx)}


@router.post("/notifications/{notification_id}/read", response_model=s.NotificationRead)
async def mark_read(notification_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await service.mark_read(ctx, notification_id)


@router.post("/notifications/read-all")
async def mark_all_read(ctx: WorkspaceContext = Write):
    return {"count": await service.mark_all_read(ctx)}


@router.get("/notification-prefs", response_model=s.PrefsMatrix)
async def get_prefs(ctx: WorkspaceContext = Read):
    return {"cells": await service.get_prefs_matrix(ctx)}


@router.put("/notification-prefs", response_model=s.PrefsMatrix)
async def put_prefs(body: s.PrefsUpdate, ctx: WorkspaceContext = Write):
    cells = await service.upsert_prefs(ctx, [c.model_dump() for c in body.cells])
    return {"cells": cells}


@router.post("/notification-prefs/unsubscribe-email")
async def unsubscribe_email(ctx: WorkspaceContext = Write):
    await service.unsubscribe_email(ctx)
    return {"ok": True}


@router.get("/needs-you", response_model=s.NeedsYouRead)
async def needs_you(ctx: WorkspaceContext = Read):
    return await list_needs_you(ctx)


@router.get("/notifications/stream")
async def notifications_stream(ctx: WorkspaceContext = Read):
    """SSE snapshot; clients should poll `/notifications/unread-count` for updates."""
    count = await service.unread_count(ctx)
    payload = json.dumps({"unread": count})

    async def gen():
        yield f"event: notifications\ndata: {payload}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
