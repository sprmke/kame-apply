"""Resume Studio API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.security import WorkspaceContext, require_action
from app.resumes import schemas as s
from app.resumes import service

router = APIRouter(tags=["resumes"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.get("/resumes", response_model=list[s.ResumeVersionRead])
async def list_resumes(
    track_id: uuid.UUID | None = None,
    profile_id: uuid.UUID | None = None,
    ctx: WorkspaceContext = Read,
):
    return await service.list_versions(ctx, track_id=track_id, profile_id=profile_id)


@router.post("/resumes", response_model=s.ResumeVersionRead, status_code=201)
async def create_resume(body: s.ResumeCreateBody, ctx: WorkspaceContext = Write):
    return await service.create_base(
        ctx,
        profile_id=body.profile_id,
        track_id=body.track_id,
        label=body.label,
        template=body.template,
        page_size=body.page_size,
    )


@router.get("/resumes/{version_id}", response_model=s.ResumeVersionRead)
async def get_resume(version_id: uuid.UUID, ctx: WorkspaceContext = Read):
    row = await service.get_version(ctx, version_id)
    return service._version_read(row)


@router.post("/resumes/{version_id}/critique", response_model=s.CritiqueRead)
async def critique_resume(version_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await service.critique(ctx, version_id)


@router.post("/resumes/{version_id}/improve", response_model=list[s.ChangeRead])
async def improve_resume(
    version_id: uuid.UUID, body: s.ImproveBody | None = None, ctx: WorkspaceContext = Write
):
    return await service.improve(ctx, version_id, window_days=(body.window_days if body else 30))


@router.get("/resumes/{version_id}/changes", response_model=list[s.ChangeRead])
async def list_changes(version_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_changes(ctx, version_id)


@router.post("/resume-changes/{change_id}", response_model=s.OkRead)
async def decide_change(
    change_id: uuid.UUID, body: s.ChangeDecisionBody, ctx: WorkspaceContext = Write
):
    await service.decide_change(ctx, change_id, status=body.status)
    return s.OkRead()


@router.post("/resumes/{version_id}/changes/bulk", response_model=s.OkRead)
async def bulk_decide(
    version_id: uuid.UUID, body: s.BulkChangesBody, ctx: WorkspaceContext = Write
):
    await service.bulk_decide(ctx, version_id, status=body.status, change_ids=body.change_ids)
    return s.OkRead()


@router.post("/resumes/{version_id}/apply", response_model=s.ResumeVersionRead)
async def apply_changes(version_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await service.apply_decisions(ctx, version_id)


@router.post("/resumes/{version_id}/render", response_model=s.RenderRead)
async def render_resume(version_id: uuid.UUID, body: s.RenderBody, ctx: WorkspaceContext = Write):
    return await service.render_version(
        ctx,
        version_id,
        template=body.template,
        page_size=body.page_size,
        broken=body.broken,
    )


@router.get("/resumes/{version_id}/parse-view", response_model=s.ParseViewRead)
async def parse_view(version_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.get_parse_view(ctx, version_id)


@router.post("/tracks/{track_id}/insights", response_model=s.InsightsRead)
async def compute_insights(
    track_id: uuid.UUID, window_days: int = 30, ctx: WorkspaceContext = Write
):
    return await service.refresh_insights(ctx, track_id, window_days=window_days)


@router.get("/tracks/{track_id}/insights", response_model=s.InsightsRead)
async def get_insights(track_id: uuid.UUID, window_days: int = 30, ctx: WorkspaceContext = Read):
    return await service.refresh_insights(ctx, track_id, window_days=window_days)
