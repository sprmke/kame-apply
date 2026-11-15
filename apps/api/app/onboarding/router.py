"""HTTP: onboarding plan (legacy) and persisted setup drafts."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query, Request

from app.core.config import Settings
from app.core.security import WorkspaceContext, require_action
from app.onboarding import pipeline, setup_service
from app.onboarding import schemas as s
from app.onboarding import service as plan_service

router = APIRouter(tags=["onboarding"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _deps(request: Request) -> pipeline.StepDeps:
    state = request.app.state
    return pipeline.StepDeps(
        settings=state.settings,
        storage=state.storage,
        run_structured=getattr(state, "run_structured", None),
        model_factory=getattr(state, "model_factory", None),
    )


def _background(request: Request) -> bool:
    return request.app.state.settings.environment in {"dev", "prod"}


@router.post("/onboarding/plan", response_model=s.OnboardingPlanRead)
async def plan(
    body: s.OnboardingPlanBody,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    runner = getattr(request.app.state, "run_structured", None)
    return await plan_service.plan_onboarding(
        ctx,
        _settings(request),
        body,
        run_structured=runner,
    )


@router.post("/onboarding/setups", response_model=s.SetupRead, status_code=202)
async def create_setup(
    body: s.SetupCreate,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    return await setup_service.create_setup(
        ctx,
        body,
        storage=request.app.state.storage,
        deps=_deps(request),
        session_factory=request.app.state.session_factory,
        background=_background(request),
    )


@router.get("/onboarding/setups", response_model=s.SetupRead | None)
async def open_setup(
    profile_id: uuid.UUID | None = Query(default=None),
    ctx: WorkspaceContext = Read,
):
    draft = await setup_service.get_open_setup(ctx, profile_id)
    return s.SetupRead.model_validate(draft) if draft is not None else None


@router.get("/onboarding/setups/provenance", response_model=s.SetupProvenanceRead | None)
async def get_provenance(
    profile_id: uuid.UUID = Query(...),
    ctx: WorkspaceContext = Read,
):
    return await setup_service.provenance(ctx, profile_id)


@router.get("/onboarding/setups/{draft_id}", response_model=s.SetupRead)
async def get_setup(draft_id: uuid.UUID, ctx: WorkspaceContext = Read):
    draft = await setup_service.get_setup(ctx, draft_id)
    return s.SetupRead.model_validate(draft)


@router.post("/onboarding/setups/{draft_id}/cancel", response_model=s.SetupRead)
async def cancel_setup(draft_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await setup_service.cancel_setup(ctx, draft_id)


@router.post("/onboarding/setups/{draft_id}/discard", response_model=s.SetupRead)
async def discard_setup(draft_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await setup_service.discard_setup(ctx, draft_id)


@router.patch("/onboarding/setups/{draft_id}/decisions", response_model=s.SetupRead)
async def patch_decisions(
    draft_id: uuid.UUID,
    body: s.SetupDecisions,
    ctx: WorkspaceContext = Write,
):
    return await setup_service.patch_decisions(ctx, draft_id, body)


@router.post("/onboarding/setups/{draft_id}/validate", response_model=s.SetupValidateRead)
async def validate_setup(draft_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await setup_service.validate_setup(ctx, draft_id)


@router.post("/onboarding/setups/{draft_id}/apply", response_model=s.SetupApplyRead)
async def apply_setup(
    draft_id: uuid.UUID,
    body: s.SetupApplyBody,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ctx: WorkspaceContext = Write,
):
    return await setup_service.apply_setup(
        ctx,
        draft_id,
        apply_key=idempotency_key or "",
        start_first_run=body.start_first_run,
        settings=request.app.state.settings,
        session_factory=request.app.state.session_factory,
    )


@router.post("/onboarding/setups/{draft_id}/revert", response_model=s.SetupRevertRead)
async def revert_setup(draft_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await setup_service.revert_setup(ctx, draft_id)


@router.post("/onboarding/setups/{draft_id}/seen", response_model=s.SetupRead)
async def mark_seen(draft_id: uuid.UUID, body: s.SetupSeen, ctx: WorkspaceContext = Write):
    return await setup_service.mark_seen(ctx, draft_id, body.page)


@router.post("/onboarding/setups/{draft_id}/retry", response_model=s.SetupRead)
async def retry_setup(
    draft_id: uuid.UUID,
    body: s.SetupRetry,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    return await setup_service.retry_setup(
        ctx,
        draft_id,
        with_ai=body.with_ai,
        deps=_deps(request),
        session_factory=request.app.state.session_factory,
        background=_background(request),
    )
