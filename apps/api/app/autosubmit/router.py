"""HTTP: auto-submit settings, explain, dry-runs, batch approve, kill switch."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.autosubmit import schemas as s
from app.autosubmit import service
from app.core.config import Settings
from app.core.security import WorkspaceContext, require_action

router = APIRouter(tags=["autosubmit"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))
Manage = Depends(require_action("workspace.update"))


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.get("/tracks/{track_id}/auto-submit", response_model=s.AutoSubmitSettingsRead)
async def get_settings(track_id: uuid.UUID, request: Request, ctx: WorkspaceContext = Read):
    return await service.get_settings(ctx, track_id, _settings(request))


@router.put("/tracks/{track_id}/auto-submit", response_model=s.AutoSubmitSettingsRead)
async def put_settings(
    track_id: uuid.UUID,
    body: s.AutoSubmitSettingsUpdate,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    return await service.update_settings(
        ctx,
        track_id,
        live_enabled=body.live_enabled,
        dry_run_remaining=body.dry_run_remaining,
        score_threshold=body.score_threshold,
        kill_switch=body.kill_switch,
        settings=_settings(request),
    )


@router.post("/workspaces/auto-submit/kill", response_model=s.BatchApproveRead)
async def workspace_kill(body: s.WorkspaceKillSwitchBody, ctx: WorkspaceContext = Manage):
    await service.set_workspace_kill(ctx, enabled=body.enabled)
    return s.BatchApproveRead(updated=1)


@router.get("/applications/{application_id}/auto-submit/explain", response_model=s.ExplainRead)
async def explain(application_id: uuid.UUID, request: Request, ctx: WorkspaceContext = Read):
    verdict = await service.evaluate_for_application(
        ctx, application_id, settings=_settings(request)
    )
    if verdict.allow_submit:
        mode = "live"
    elif verdict.dry_run:
        mode = "dry_run"
    elif any(r.code == "autonomy" and not r.ok for r in verdict.reasons):
        mode = "assist"
    else:
        mode = "blocked"
    return s.ExplainRead(application_id=application_id, verdict=verdict, mode=mode)


@router.get("/tracks/{track_id}/auto-submit/dry-runs", response_model=list[s.DryRunReportRead])
async def dry_runs(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_dry_runs(ctx, track_id)


@router.post("/auto-submit/batch-approve", response_model=s.BatchApproveRead)
async def batch_approve(body: s.BatchApproveBody, ctx: WorkspaceContext = Write):
    n = await service.batch_approve_answers(
        ctx, answer_bank_ids=body.answer_bank_ids, approved=body.approved
    )
    return s.BatchApproveRead(updated=n)


@router.get("/tracks/{track_id}/auto-submit/anomaly", response_model=s.AnomalyStatusRead)
async def anomaly(track_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.anomaly_status(ctx, track_id)
