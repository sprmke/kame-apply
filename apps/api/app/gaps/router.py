"""HTTP: gap plan."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.security import WorkspaceContext, require_action
from app.gaps import schemas as s
from app.gaps import service

router = APIRouter(tags=["gaps"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.get("/tracks/{track_id}/gap-plan", response_model=list[s.GapPlanItemRead])
async def list_gap_plan(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_items(ctx, track_id)


@router.post("/tracks/{track_id}/gap-plan/refresh", response_model=list[s.GapPlanItemRead])
async def refresh_gap_plan(track_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await service.refresh_suggestions(ctx, track_id)


@router.patch("/gap-plan/{item_id}", response_model=s.GapPlanItemRead)
async def patch_gap_item(
    item_id: uuid.UUID, body: s.GapStatusUpdate, ctx: WorkspaceContext = Write
):
    return await service.update_status(ctx, item_id, status=body.status)
