"""HTTP: apply runs, checkpoints, runner claim/heartbeat/steps."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext, require_action
from app.extension import schemas as ext_schemas
from app.extension import service as ext_service
from app.runs import schemas as s
from app.runs import service
from app.runs.deps import require_runner_action
from app.runs.live_hub import get_live_hub
from app.runs.live_tokens import issue_live_token
from app.runs.workflow import signal_run_done, start_apply_workflow

router = APIRouter(prefix="/runs", tags=["runs"])

JwtWrite = Depends(require_action("data.write"))
JwtRead = Depends(require_action("data.read"))
JwtManage = Depends(require_action("workspace.update"))
RunnerWrite = Depends(require_runner_action("data.write"))
RunnerRead = Depends(require_runner_action("data.read"))


@router.post("/tokens", response_model=s.RunnerTokenCreated, status_code=201)
async def create_runner_token(body: s.RunnerTokenCreate, ctx: WorkspaceContext = JwtManage):
    row, raw = await service.create_runner_token(ctx, label=body.label, mode=body.mode)
    return s.RunnerTokenCreated(id=row.id, token=raw, label=row.label, mode=row.mode)


@router.get("/tokens", response_model=list[s.RunnerTokenRead])
async def list_runner_tokens(ctx: WorkspaceContext = JwtManage):
    return [
        s.RunnerTokenRead(
            id=t.id,
            label=t.label,
            mode=t.mode,
            last_seen_at=t.last_seen_at,
            created_at=t.created_at,
        )
        for t in await service.list_runner_tokens(ctx)
    ]


@router.post("/tokens/{token_id}/revoke", response_model=s.OkRead)
async def revoke_runner_token(token_id: uuid.UUID, ctx: WorkspaceContext = JwtManage):
    await service.revoke_runner_token(ctx, token_id)
    return s.OkRead()


@router.post("/runner/start", response_model=s.ApplyRunRead, status_code=201)
async def start_runner(body: s.StartRunnerBody, request: Request, ctx: WorkspaceContext = JwtWrite):
    run = await service.start_runner(
        ctx,
        application_id=body.application_id,
        allow_submit=body.allow_submit,
        settings=request.app.state.settings,
    )
    wf = start_apply_workflow(str(ctx.workspace_id), str(run.id))
    if wf:
        run.dbos_workflow_id = wf
    return s.ApplyRunRead(**service.run_to_read(run))


@router.get("/", response_model=list[s.ApplyRunRead])
async def list_runs(application_id: uuid.UUID | None = None, ctx: WorkspaceContext = JwtRead):
    return [
        s.ApplyRunRead(**service.run_to_read(r))
        for r in await service.list_runs(ctx, application_id=application_id)
    ]


@router.get("/{run_id}", response_model=s.ApplyRunRead)
async def get_run(run_id: uuid.UUID, ctx: WorkspaceContext = RunnerRead):
    return s.ApplyRunRead(**service.run_to_read(await service.get_run(ctx, run_id)))


@router.get("/{run_id}/steps", response_model=list[s.ApplyRunStepRead])
async def list_steps(run_id: uuid.UUID, ctx: WorkspaceContext = RunnerRead):
    return [
        s.ApplyRunStepRead(
            id=st.id,
            seq=st.seq,
            page_url=st.page_url,
            action=st.action,
            field_label=st.field_label,
            value_redacted=st.value_redacted,
            canonical_key=st.canonical_key,
            source_fact_ref=st.source_fact_ref,
            pii_class=st.pii_class,
            screenshot_r2=st.screenshot_r2,
            outcome=st.outcome,
            created_at=st.created_at,
        )
        for st in await service.list_steps(ctx, run_id)
    ]


@router.get("/{run_id}/checkpoints", response_model=list[s.CheckpointRead])
async def list_checkpoints(run_id: uuid.UUID, ctx: WorkspaceContext = RunnerRead):
    return [
        s.CheckpointRead(
            id=c.id,
            run_id=c.run_id,
            kind=c.kind,
            detail=c.detail,
            status=c.status,
            decision=c.decision,
            decided_at=c.decided_at,
            created_at=c.created_at,
        )
        for c in await service.list_checkpoints(ctx, run_id)
    ]


@router.post("/checkpoints/{checkpoint_id}/resolve", response_model=s.CheckpointRead)
async def resolve_checkpoint(
    checkpoint_id: uuid.UUID,
    body: s.CheckpointResolveBody,
    ctx: WorkspaceContext = RunnerWrite,
):
    # RunnerWrite also accepts JWT members (via runner_workspace_context fallback).
    c = await service.resolve_checkpoint(
        ctx, checkpoint_id, decision=body.decision, value=body.value, note=body.note
    )
    return s.CheckpointRead(
        id=c.id,
        run_id=c.run_id,
        kind=c.kind,
        detail=c.detail,
        status=c.status,
        decision=c.decision,
        decided_at=c.decided_at,
        created_at=c.created_at,
    )


@router.post("/{run_id}/handoff", response_model=s.HandoffRead)
async def handoff(run_id: uuid.UUID, ctx: WorkspaceContext = JwtWrite):
    data = await service.handoff(ctx, run_id)
    return s.HandoffRead(**data)


# --- Live view (Phase 16) ------------------------------------------------------------------


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.post("/{run_id}/live/token", response_model=s.LiveTokenRead)
async def mint_live_viewer_token(
    run_id: uuid.UUID, request: Request, ctx: WorkspaceContext = JwtRead
):
    run = await service.get_run(ctx, run_id)
    settings = _settings(request)
    token, exp = issue_live_token(
        settings,
        run_id=run.id,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        role="viewer",
    )
    if run.live_mode == "off":
        await service.set_live_mode(ctx, run_id, live_mode="screencast")
    return s.LiveTokenRead(
        token=token,
        role="viewer",
        ws_path=f"/api/v1/runs/{run.id}/live",
        expires_at=exp,
        run_id=run.id,
    )


@router.post("/{run_id}/live/runner-token", response_model=s.LiveTokenRead)
async def mint_live_runner_token(
    run_id: uuid.UUID, request: Request, ctx: WorkspaceContext = RunnerWrite
):
    run = await service.get_run(ctx, run_id)
    settings = _settings(request)
    token, exp = issue_live_token(
        settings,
        run_id=run.id,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        role="runner",
    )
    if run.live_mode == "off":
        await service.set_live_mode(ctx, run_id, live_mode="screencast")
    return s.LiveTokenRead(
        token=token,
        role="runner",
        ws_path=f"/api/v1/runs/{run.id}/live",
        expires_at=exp,
        run_id=run.id,
    )


@router.get("/{run_id}/live/state", response_model=s.LiveStateRead)
async def live_state(run_id: uuid.UUID, ctx: WorkspaceContext = JwtRead):
    run = await service.get_run(ctx, run_id)
    hub = get_live_hub()
    room = hub.get(run.id)
    return s.LiveStateRead(
        run_id=run.id,
        control_mode=run.control_mode,
        live_mode=run.live_mode,
        controller_user_id=run.controller_user_id,
        viewers=room.viewer_count() if room else 0,
        user_edited_fields=list(run.user_edited_fields or []),
        telemetry=dict(run.live_telemetry or {}),
    )


@router.post("/{run_id}/live/takeover", response_model=s.LiveStateRead)
async def live_takeover(run_id: uuid.UUID, ctx: WorkspaceContext = JwtWrite):
    run = await service.set_control_mode(ctx, run_id, mode="human", controller_user_id=ctx.user_id)
    if run.live_mode == "off":
        run = await service.set_live_mode(ctx, run_id, live_mode="screencast")
    hub = get_live_hub()
    room = hub.get(run.id)
    if room:
        async with room.lock:
            room.control_mode = "human"
            room.controller_user_id = ctx.user_id
        await hub.send_to_runner(
            room,
            {
                "type": "control",
                "mode": "human",
                "controller_user_id": str(ctx.user_id),
            },
        )
        await hub.broadcast_presence(room)
    return s.LiveStateRead(
        run_id=run.id,
        control_mode=run.control_mode,
        live_mode=run.live_mode,
        controller_user_id=run.controller_user_id,
        viewers=room.viewer_count() if room else 0,
        user_edited_fields=list(run.user_edited_fields or []),
        telemetry=dict(run.live_telemetry or {}),
    )


@router.post("/{run_id}/live/handback", response_model=s.LiveStateRead)
async def live_handback(run_id: uuid.UUID, ctx: WorkspaceContext = JwtWrite):
    run = await service.get_run(ctx, run_id)
    if run.controller_user_id and run.controller_user_id != ctx.user_id:
        raise AppError("forbidden", "You do not have permission to do this", 403)
    run = await service.set_control_mode(ctx, run_id, mode="agent")
    hub = get_live_hub()
    room = hub.get(run.id)
    if room:
        async with room.lock:
            room.control_mode = "agent"
            room.controller_user_id = None
        await hub.send_to_runner(room, {"type": "control", "mode": "agent", "reextract": True})
        await hub.broadcast_presence(room)
    return s.LiveStateRead(
        run_id=run.id,
        control_mode=run.control_mode,
        live_mode=run.live_mode,
        controller_user_id=run.controller_user_id,
        viewers=room.viewer_count() if room else 0,
        user_edited_fields=list(run.user_edited_fields or []),
        telemetry=dict(run.live_telemetry or {}),
    )


@router.patch("/{run_id}/live/mode", response_model=s.LiveStateRead)
async def live_mode(run_id: uuid.UUID, body: s.LiveModeBody, ctx: WorkspaceContext = JwtWrite):
    run = await service.set_live_mode(ctx, run_id, live_mode=body.live_mode)
    hub = get_live_hub()
    room = hub.get(run.id)
    if room:
        async with room.lock:
            room.live_mode = body.live_mode
        await hub.send_to_runner(room, {"type": "mode", "live_mode": body.live_mode})
        await hub.broadcast_presence(room)
    return s.LiveStateRead(
        run_id=run.id,
        control_mode=run.control_mode,
        live_mode=run.live_mode,
        controller_user_id=run.controller_user_id,
        viewers=room.viewer_count() if room else 0,
        user_edited_fields=list(run.user_edited_fields or []),
        telemetry=dict(run.live_telemetry or {}),
    )


@router.post("/{run_id}/live/field-lock", response_model=s.OkRead)
async def live_field_lock(
    run_id: uuid.UUID, body: s.LiveFieldLockBody, ctx: WorkspaceContext = RunnerWrite
):
    await service.lock_user_edited_field(ctx, run_id, field_id=body.field_id, label=body.label)
    return s.OkRead()


# --- Runner pull protocol ------------------------------------------------------------------


@router.post("/runner/claim", response_model=None)
async def claim(body: s.ClaimBody, ctx: WorkspaceContext = RunnerWrite):
    run = await service.claim_next(ctx, runner_id=body.runner_id)
    if run is None:
        return Response(status_code=204)
    return JSONResponse(
        status_code=200,
        content=s.ApplyRunRead(**service.run_to_read(run)).model_dump(mode="json"),
    )


@router.post("/{run_id}/heartbeat", response_model=s.ApplyRunRead)
async def heartbeat(run_id: uuid.UUID, body: s.HeartbeatBody, ctx: WorkspaceContext = RunnerWrite):
    run = await service.heartbeat(ctx, run_id, runner_id=body.runner_id, page_url=body.page_url)
    return s.ApplyRunRead(**service.run_to_read(run))


@router.post("/{run_id}/plan-page", response_model=ext_schemas.PlanPageResult)
async def plan_page_for_run(
    run_id: uuid.UUID, body: ext_schemas.PlanPageBody, ctx: WorkspaceContext = RunnerWrite
):
    run = await service.get_run(ctx, run_id)
    body.run_id = run.id
    body.profile_id = run.profile_id
    body.platform = body.platform or run.ats or run.platform
    body.page_url = body.page_url or run.page_url
    body.application_id = body.application_id or run.application_id
    body.job_id = body.job_id or run.job_id
    body.track_id = body.track_id or run.track_id
    return await ext_service.plan_page(ctx, body)


@router.post("/{run_id}/steps", response_model=s.ApplyRunStepRead, status_code=201)
async def upload_step(
    run_id: uuid.UUID, body: s.StepUploadBody, ctx: WorkspaceContext = RunnerWrite
):
    st = await service.append_step(ctx, run_id, body.model_dump())
    return s.ApplyRunStepRead(
        id=st.id,
        seq=st.seq,
        page_url=st.page_url,
        action=st.action,
        field_label=st.field_label,
        value_redacted=st.value_redacted,
        canonical_key=st.canonical_key,
        source_fact_ref=st.source_fact_ref,
        pii_class=st.pii_class,
        screenshot_r2=st.screenshot_r2,
        outcome=st.outcome,
        created_at=st.created_at,
    )


@router.post("/{run_id}/checkpoints", response_model=s.CheckpointRead, status_code=201)
async def create_checkpoint(
    run_id: uuid.UUID, body: s.CheckpointCreateBody, ctx: WorkspaceContext = RunnerWrite
):
    c = await service.open_checkpoint(ctx, run_id, kind=body.kind, detail=body.detail)
    return s.CheckpointRead(
        id=c.id,
        run_id=c.run_id,
        kind=c.kind,
        detail=c.detail,
        status=c.status,
        decision=c.decision,
        decided_at=c.decided_at,
        created_at=c.created_at,
    )


@router.get("/{run_id}/ephemeral-sensitive")
async def ephemeral_sensitive(run_id: uuid.UUID, ctx: WorkspaceContext = RunnerWrite):
    value = await service.pop_ephemeral_sensitive(ctx, run_id)
    return {"value": value}


@router.post("/{run_id}/complete", response_model=s.ApplyRunRead)
async def complete(
    run_id: uuid.UUID,
    status: str = "completed",
    confirmation: bool = False,
    failure_reason: str | None = None,
    ctx: WorkspaceContext = RunnerWrite,
):
    run = await service.complete_run(
        ctx, run_id, status=status, failure_reason=failure_reason, confirmation=confirmation
    )
    signal_run_done(str(run_id), {"status": status, "confirmation": confirmation})
    return s.ApplyRunRead(**service.run_to_read(run))
