"""Safety API: risk, Check-this, PII classify, mid-run signals."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.security import WorkspaceContext, require_action
from app.safety import schemas as s
from app.safety import service
from app.safety import workflows as wf

router = APIRouter(tags=["safety"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.get("/safety/flagged", response_model=list[s.FlaggedJobRead])
async def flagged_jobs(ctx: WorkspaceContext = Read):
    return await service.list_flagged(ctx)


@router.get("/jobs/{job_id}/risk", response_model=s.JobRiskRead)
async def get_risk(job_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.get_job_risk(ctx, job_id)


@router.post("/jobs/{job_id}/risk/assess", response_model=s.AssessResultRead)
async def assess_risk(job_id: uuid.UUID, ctx: WorkspaceContext = Write):
    row = await service.assess_and_store(ctx, job_id, run_network=True, run_llm=False)
    # Enqueue durable follow-up for network-heavy refresh when DBOS is configured.
    wf.enqueue_assess_job_risk(str(ctx.workspace_id), str(job_id))
    return s.AssessResultRead(
        job_id=row.job_id, level=row.level, score=row.score, partial=row.partial
    )


@router.post("/jobs/{job_id}/risk/decision", response_model=s.OkRead)
async def risk_decision(job_id: uuid.UUID, body: s.RiskDecisionBody, ctx: WorkspaceContext = Write):
    await service.decide(
        ctx,
        job_id,
        decision=body.decision,
        note=body.note,
        confirm_risk=body.confirm_risk,
    )
    return s.OkRead()


@router.post("/safety/mid-run", response_model=s.AssessResultRead)
async def mid_run(body: s.MidRunSignalBody, ctx: WorkspaceContext = Write):
    row = await service.mid_run_signals(ctx, body.job_id, body.signals)
    return s.AssessResultRead(
        job_id=row.job_id, level=row.level, score=row.score, partial=row.partial
    )


@router.post("/safety/check-this", response_model=s.CheckThisRead)
async def check_this(body: s.CheckThisBody, ctx: WorkspaceContext = Read):
    # activity-log: N/A — read-only analysis; no persisted workspace mutation
    _ = ctx
    return service.run_check_this(text=body.text, url=body.url)


@router.post("/safety/classify-field", response_model=s.FieldClassifyRead)
async def classify_field_endpoint(body: s.FieldClassifyBody, ctx: WorkspaceContext = Read):
    _ = ctx
    return service.classify_form_field(
        label=body.label,
        name=body.name,
        autocomplete=body.autocomplete,
        input_type=body.input_type,
        pattern=body.pattern,
        country=body.country,
    )
