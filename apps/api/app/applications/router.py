"""Tailor + applications tracker + home + metrics API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.applications import home as home_svc
from app.applications import metrics as metrics_svc
from app.applications import schemas as s
from app.applications import service, tracker
from app.core.security import WorkspaceContext, require_action

router = APIRouter(tags=["applications"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.post(
    "/track-jobs/{track_job_id}/tailor",
    response_model=s.TailorRunRead,
    status_code=201,
)
async def start_tailor(
    track_job_id: uuid.UUID,
    request: Request,
    body: s.TailorStartBody | None = None,
    ctx: WorkspaceContext = Write,
):
    body = body or s.TailorStartBody()
    return await service.start_tailor(
        ctx,
        track_job_id,
        include_cover_letter=body.include_cover_letter,
        base_version_id=body.base_version_id,
        run_structured=getattr(request.app.state, "run_structured", None),
        model_factory=getattr(request.app.state, "model_factory", None),
    )


@router.get("/tailor-runs/{run_id}", response_model=s.TailorRunRead)
async def get_tailor_run(run_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.get_tailor_run(ctx, run_id)


@router.post("/tailor-runs/{run_id}/accept", response_model=s.ApplicationRead)
async def accept_tailor(
    run_id: uuid.UUID, body: s.TailorAcceptBody | None = None, ctx: WorkspaceContext = Write
):
    body = body or s.TailorAcceptBody()
    return await service.accept_tailor(
        ctx,
        run_id,
        include_cover_letter=body.include_cover_letter,
        method=body.method,
    )


@router.get("/applications", response_model=s.ApplicationListRead)
async def list_applications(
    track_id: uuid.UUID | None = None,
    status: str | None = None,
    method: str | None = None,
    q: str | None = None,
    submitted_from: datetime | None = None,
    submitted_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: WorkspaceContext = Read,
):
    return await tracker.list_applications(
        ctx,
        track_id=track_id,
        status=status,
        method=method,
        q=q,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
        limit=limit,
        offset=offset,
    )


@router.get("/applications/export")
async def export_applications(fmt: Literal["json", "csv"] = "json", ctx: WorkspaceContext = Read):
    filename, body, media = await tracker.export_applications(ctx, fmt=fmt)
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/applications/mark-applied", response_model=s.ApplicationRead, status_code=201)
async def mark_applied(body: s.MarkAppliedBody, request: Request, ctx: WorkspaceContext = Write):
    return await tracker.mark_applied_from_job(
        ctx,
        track_job_id=body.track_job_id,
        job_id=body.job_id,
        track_id=body.track_id,
        method=body.method,
        notes=body.notes,
        storage=getattr(request.app.state, "storage", None),
    )


@router.post("/applications/manual", response_model=s.ApplicationRead, status_code=201)
async def create_manual(body: s.ManualCreateBody, ctx: WorkspaceContext = Write):
    return await tracker.create_manual(
        ctx,
        track_id=body.track_id,
        company=body.company,
        title=body.title,
        url=body.url,
        method=body.method,
        notes=body.notes,
        mark_submitted=body.mark_submitted,
    )


@router.post("/applications/suggest-ghosted")
async def suggest_ghosted(
    days: int = Query(default=14, ge=7, le=60), ctx: WorkspaceContext = Write
):
    return {"items": await tracker.suggest_ghosted(ctx, days=days)}


@router.get("/applications/{app_id}", response_model=s.ApplicationRead)
async def get_application(app_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await tracker.get_application_detail(ctx, app_id)


@router.patch("/applications/{app_id}/status", response_model=s.ApplicationRead)
async def patch_status(
    app_id: uuid.UUID,
    body: s.ApplicationStatusBody,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    return await tracker.update_status(
        ctx,
        app_id,
        status=body.status,
        note=body.note,
        storage=getattr(request.app.state, "storage", None),
    )


@router.patch("/applications/{app_id}/notes", response_model=s.ApplicationRead)
async def patch_notes(
    app_id: uuid.UUID, body: s.ApplicationNotesBody, ctx: WorkspaceContext = Write
):
    return await tracker.update_notes(ctx, app_id, body.notes)


@router.get("/application-views")
async def list_views(ctx: WorkspaceContext = Read):
    return await tracker.list_saved_views(ctx)


@router.post("/application-views", status_code=201)
async def create_view(body: s.SavedViewBody, ctx: WorkspaceContext = Write):
    return await tracker.save_view(ctx, name=body.name, filters=body.filters)


@router.get("/metrics")
async def metrics(
    period: Literal["today", "week", "total"] = "week",
    track_id: uuid.UUID | None = None,
    ctx: WorkspaceContext = Read,
):
    return await metrics_svc.compute_kpis(ctx, period=period, track_id=track_id, tz_name="UTC")


@router.get("/home")
async def home(
    period: Literal["today", "week", "total"] = "week",
    ctx: WorkspaceContext = Read,
):
    return await home_svc.home_brief(ctx, period=period)
