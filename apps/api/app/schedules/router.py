"""HTTP: schedules, tick hook, run history, track pause/resume."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request

from app.core.security import WorkspaceContext, require_action
from app.schedules import schemas as s
from app.schedules import service
from app.schedules.dispatcher import tick
from app.tracks import schemas as track_schemas
from app.tracks.service import PREVIEW_MESSAGE

router = APIRouter(tags=["schedules"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


def _track_read(track) -> track_schemas.TrackRead:
    data = {
        "id": track.id,
        "workspace_id": track.workspace_id,
        "profile_id": track.profile_id,
        "name": track.name,
        "icon": track.icon,
        "color_hue": track.color_hue,
        "status": track.status,
        "autonomy": track.autonomy,
        "sort_order": track.sort_order,
        "summary": track.summary or "",
        "settings": dict(track.settings or {}),
        "template_slug": track.template_slug,
        "created_at": track.created_at,
        "updated_at": track.updated_at,
        "archived_at": track.archived_at,
        "preview_message": PREVIEW_MESSAGE,
    }
    return track_schemas.TrackRead.model_validate(data)


@router.get("/tracks/{track_id}/schedules", response_model=list[s.ScheduleRead])
async def list_schedules(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_schedules(ctx, track_id)


@router.post("/tracks/{track_id}/schedules", response_model=s.ScheduleRead, status_code=201)
async def create_schedule(
    track_id: uuid.UUID, body: s.ScheduleCreate, ctx: WorkspaceContext = Write
):
    return await service.create_schedule(ctx, track_id, body.model_dump())


@router.patch("/schedules/{schedule_id}", response_model=s.ScheduleRead)
async def update_schedule(
    schedule_id: uuid.UUID, body: s.ScheduleUpdate, ctx: WorkspaceContext = Write
):
    return await service.update_schedule(ctx, schedule_id, body.model_dump(exclude_unset=True))


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: uuid.UUID, ctx: WorkspaceContext = Write):
    await service.delete_schedule(ctx, schedule_id)


@router.post("/tracks/{track_id}/pause", response_model=track_schemas.TrackRead)
async def pause_track(track_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return _track_read(await service.pause_track(ctx, track_id))


@router.post("/tracks/{track_id}/resume", response_model=track_schemas.TrackRead)
async def resume_track(track_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return _track_read(await service.resume_track(ctx, track_id))


@router.get("/tracks/{track_id}/runs", response_model=list[s.DiscoveryRunHistoryRead])
async def run_history(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_run_history(ctx, track_id)


@router.post("/schedules/tick", response_model=s.TickResult)
async def schedules_tick(
    request: Request,
    body: s.TickBody | None = None,
    ctx: WorkspaceContext = Write,
):
    """Advance due schedules. Pass `now` to freeze time in tests/dev."""
    body = body or s.TickBody()
    now: datetime | None = body.now
    mailer = getattr(request.app.state, "mailer", None)
    ws = ctx.workspace_id if body.workspace_only else None
    result = await tick(ctx.session, now=now, workspace_id=ws, mailer=mailer)
    return result
