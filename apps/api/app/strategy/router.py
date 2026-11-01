"""HTTP: Be Found + strategy endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.security import WorkspaceContext, require_action
from app.strategy import schemas as s
from app.strategy import service

router = APIRouter(tags=["strategy"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.get("/tracks/{track_id}/linkedin-optimize", response_model=s.LinkedInOptimizeRead)
async def linkedin_optimize(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.optimize_linkedin(ctx, track_id)


@router.post("/strategy/consistency", response_model=s.ConsistencyReport)
async def consistency(body: s.ConsistencyBody, ctx: WorkspaceContext = Write):
    return await service.consistency_report(
        ctx, linkedin_text=body.linkedin_text, track_id=body.track_id
    )


@router.get("/strategy/prefs", response_model=s.StrategyPrefRead)
async def get_prefs(ctx: WorkspaceContext = Read):
    return await service.get_prefs(ctx)


@router.put("/strategy/prefs", response_model=s.StrategyPrefRead)
async def put_prefs(body: s.StrategyPrefUpdate, ctx: WorkspaceContext = Write):
    return await service.update_prefs(
        ctx, company_cap=body.company_cap, window_days=body.company_cap_window_days
    )


@router.get("/applications/{application_id}/company-cap", response_model=s.CapCheckRead)
async def company_cap(application_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.company_cap_for_application(ctx, application_id)


@router.get("/jobs/{job_id}/freshness", response_model=s.FreshnessRead)
async def freshness(job_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.job_freshness(ctx, job_id)


@router.get("/applications/{application_id}/salary-advice", response_model=s.SalaryAdviceRead)
async def salary_advice(application_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.salary_for_application(ctx, application_id)


@router.get("/applications/{application_id}/follow-up-drafts", response_model=s.FollowUpDraftsRead)
async def follow_ups(application_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.follow_up_drafts(ctx, application_id)
