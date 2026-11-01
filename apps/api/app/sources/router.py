"""HTTP: source health, track sources, discovery runs, careers add, track jobs."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.companies import service as company_service
from app.core.security import WorkspaceContext, require_action
from app.sources import schemas as s
from app.sources import service

router = APIRouter(tags=["sources"])
Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))
AdminRead = Depends(require_action("activity.read"))


@router.get("/sources/health", response_model=list[s.SourceHealthRead])
async def source_health(ctx: WorkspaceContext = AdminRead):
    return await service.list_source_health(ctx.session)


@router.get("/sources/directory/stats", response_model=s.DirectoryStatsRead)
async def directory_stats(ctx: WorkspaceContext = Read):
    return await company_service.directory_stats(ctx.session)


@router.post("/sources/careers", response_model=s.CompanyBoardRead, status_code=201)
async def add_careers(body: s.AddCareersIn, ctx: WorkspaceContext = Write):
    return await company_service.add_careers_url(ctx, body.url)


@router.get("/tracks/{track_id}/sources", response_model=list[s.TrackSourceRead])
async def track_sources(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_track_sources(ctx, track_id)


@router.patch("/tracks/{track_id}/sources/{source_id}", response_model=s.TrackSourceRead)
async def patch_track_source(
    track_id: uuid.UUID,
    source_id: uuid.UUID,
    body: s.TrackSourceUpdate,
    ctx: WorkspaceContext = Write,
):
    return await service.update_track_source(
        ctx, track_id, source_id, enabled=body.enabled, params=body.params
    )


@router.post("/tracks/{track_id}/discover", response_model=s.DiscoveryRunRead, status_code=201)
async def discover_now(track_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await service.start_discovery(ctx, track_id)


@router.get("/discovery-runs/{run_id}", response_model=s.DiscoveryRunRead)
async def get_discovery_run(run_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.get_run(ctx, run_id)


@router.get("/tracks/{track_id}/jobs", response_model=list[s.TrackJobRead])
async def track_jobs(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_track_jobs(ctx, track_id)


@router.get("/discovery-runs/{run_id}/events")
async def discovery_events(run_id: uuid.UUID, ctx: WorkspaceContext = Read):
    """SSE progress stream for Run now."""

    async def gen():
        for _ in range(60):
            run = await service.get_run(ctx, run_id)
            payload = {
                "status": run.status,
                "progress": run.progress,
                "error": run.error,
            }
            yield f"data: {json.dumps(payload)}\n\n"
            if run.status in ("succeeded", "failed", "cancelled"):
                break
            await asyncio.sleep(0.5)
            await ctx.session.refresh(run)

    return StreamingResponse(gen(), media_type="text/event-stream")
