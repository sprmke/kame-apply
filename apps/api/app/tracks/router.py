"""HTTP surface for Tracks and criteria."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext, require_action
from app.tracks import schemas as s
from app.tracks import service

router = APIRouter(prefix="/tracks", tags=["tracks"])
Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _track_read(track) -> s.TrackRead:
    return s.TrackRead.model_validate(
        {
            **{c.name: getattr(track, c.name) for c in track.__table__.columns},
            "preview_message": service.PREVIEW_MESSAGE,
        }
    )


@router.get("", response_model=list[s.TrackRead])
async def list_tracks(
    include_archived: bool = False,
    ctx: WorkspaceContext = Read,
):
    rows = await service.list_tracks(ctx, include_archived=include_archived)
    return [_track_read(r) for r in rows]


@router.post("", response_model=s.TrackDetail, status_code=201)
async def create_track(body: s.TrackCreate, ctx: WorkspaceContext = Write):
    detail = await service.create_track(ctx, body)
    return s.TrackDetail(
        **_track_read(detail["track"]).model_dump(),
        criteria=s.TrackCriteriaRead.model_validate(detail["criteria"]),
    )


@router.get("/templates", response_model=list[s.TrackTemplateRead])
async def list_templates(ctx: WorkspaceContext = Read):
    return await service.list_templates(ctx)


@router.post("/reorder", response_model=list[s.TrackRead])
async def reorder(body: s.TrackReorder, ctx: WorkspaceContext = Write):
    rows = await service.reorder_tracks(ctx, body.ordered_ids)
    return [_track_read(r) for r in rows]


@router.get("/geo/lookup", response_model=s.GeocodeRead)
async def geo_lookup(
    place: Annotated[str, Query(min_length=1, max_length=200)],
    ctx: WorkspaceContext = Read,
):
    hit = await service.geocode(ctx, place, allow_network=True)
    if hit is None:
        raise AppError("geocode_not_found", "Place not found", 404)
    return s.GeocodeRead(
        place=hit.place,
        lat=hit.lat,
        lon=hit.lon,
        country=hit.country,
        display_name=hit.display_name,
        cached=hit.cached,
    )


@router.get("/{track_id}", response_model=s.TrackDetail)
async def get_track(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    detail = await service.get_detail(ctx, track_id)
    return s.TrackDetail(
        **_track_read(detail["track"]).model_dump(),
        criteria=s.TrackCriteriaRead.model_validate(detail["criteria"]),
    )


@router.patch("/{track_id}", response_model=s.TrackRead)
async def update_track(track_id: uuid.UUID, body: s.TrackUpdate, ctx: WorkspaceContext = Write):
    return _track_read(await service.update_track(ctx, track_id, body))


@router.post("/{track_id}/duplicate", response_model=s.TrackDetail, status_code=201)
async def duplicate(track_id: uuid.UUID, ctx: WorkspaceContext = Write):
    detail = await service.duplicate_track(ctx, track_id)
    return s.TrackDetail(
        **_track_read(detail["track"]).model_dump(),
        criteria=s.TrackCriteriaRead.model_validate(detail["criteria"]),
    )


@router.post("/{track_id}/archive", response_model=s.TrackRead)
async def archive(track_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return _track_read(await service.archive_track(ctx, track_id))


@router.put("/{track_id}/criteria", response_model=s.TrackDetail)
async def put_criteria(track_id: uuid.UUID, body: s.CriteriaPut, ctx: WorkspaceContext = Write):
    detail = await service.put_criteria(ctx, track_id, body)
    return s.TrackDetail(
        **_track_read(detail["track"]).model_dump(),
        criteria=s.TrackCriteriaRead.model_validate(detail["criteria"]),
    )


@router.post("/{track_id}/criteria/compile", response_model=s.CriteriaCompilePreview)
async def compile_criteria(
    track_id: uuid.UUID,
    body: s.CriteriaCompileRequest,
    request: Request,
    settings: SettingsDep,
    ctx: WorkspaceContext = Write,
):
    runner = getattr(request.app.state, "run_structured", None)
    kwargs = {}
    if runner is not None:
        kwargs["run_structured"] = runner
    result = await service.compile_and_maybe_apply(
        ctx,
        settings,
        track_id,
        text=body.text,
        apply=body.apply,
        **kwargs,
    )
    return s.CriteriaCompilePreview(
        criteria=result["criteria"],
        summary=result["summary"],
        diff=result["diff"],
        warnings=result["warnings"],
        invented_fields=result.get("invented_fields") or [],
    )
