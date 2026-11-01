"""Matching / job board API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.core.security import WorkspaceContext, require_action
from app.matching import schemas as s
from app.matching import service

router = APIRouter(tags=["matching"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.get("/jobs", response_model=list[s.BoardJobRead])
async def list_jobs(
    track_id: uuid.UUID | None = None,
    status: str | None = None,
    include_not_eligible: bool = False,
    sort: str = Query(default="score", pattern="^(score|newest|salary)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: WorkspaceContext = Read,
):
    return await service.list_board(
        ctx,
        track_id=track_id,
        status=status,
        include_not_eligible=include_not_eligible,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/export.csv")
async def export_jobs_csv(
    track_id: uuid.UUID | None = None,
    include_not_eligible: bool = False,
    ctx: WorkspaceContext = Read,
):
    body = await service.export_csv(
        ctx, track_id=track_id, include_not_eligible=include_not_eligible
    )
    return PlainTextResponse(
        body,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs.csv"},
    )


@router.get("/track-jobs/{track_job_id}", response_model=s.JobDetailRead)
async def track_job_detail(track_job_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.get_track_job_detail(ctx, track_job_id)


@router.post("/track-jobs/{track_job_id}/triage", response_model=s.OkRead)
async def triage_job(track_job_id: uuid.UUID, body: s.TriageBody, ctx: WorkspaceContext = Write):
    await service.triage(ctx, track_job_id, action=body.action, skip_reason=body.skip_reason)
    return s.OkRead()


@router.post("/tracks/{track_id}/score", response_model=s.ScoreResultRead)
async def score_track(track_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await service.score_track_jobs(ctx, track_id)


@router.get("/tracks/{track_id}/relaxations", response_model=list[s.RelaxationRead])
async def relaxations(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.relaxation_suggestions(ctx, track_id)


@router.post("/hidden-companies", response_model=s.OkRead, status_code=201)
async def hide_company(body: s.HideCompanyBody, ctx: WorkspaceContext = Write):
    await service.hide_company(
        ctx, company_id=body.company_id, track_id=body.track_id, reason=body.reason
    )
    return s.OkRead()
