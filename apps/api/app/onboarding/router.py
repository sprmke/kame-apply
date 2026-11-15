"""HTTP: onboarding plan. Read-only draft bundle; every accept uses its normal endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings
from app.core.security import WorkspaceContext, require_action
from app.onboarding import schemas as s
from app.onboarding import service

router = APIRouter(tags=["onboarding"])

Write = Depends(require_action("data.write"))


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.post("/onboarding/plan", response_model=s.OnboardingPlanRead)
async def plan(
    body: s.OnboardingPlanBody,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    runner = getattr(request.app.state, "run_structured", None)
    return await service.plan_onboarding(
        ctx,
        _settings(request),
        body,
        run_structured=runner,
    )
