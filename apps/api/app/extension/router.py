"""Browser extension HTTP surface."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.ratelimit import client_ip
from app.core.security import WorkspaceContext, require_action
from app.extension import schemas as s
from app.extension import service as svc
from app.extension.deps import require_extension_action
from app.extension.platforms import PLATFORM_TERMS, RESTRICTED_PLATFORMS

router = APIRouter(prefix="/extension", tags=["extension"])

JwtWrite = Depends(require_action("data.write"))
JwtManage = Depends(require_action("workspace.update"))
JwtRead = Depends(require_action("data.read"))
ExtRead = Depends(require_extension_action("data.read"))
ExtWrite = Depends(require_extension_action("data.write"))


@router.post("/tokens", response_model=s.ExtensionTokenCreated, status_code=201)
async def create_token(
    request: Request, body: s.ExtensionTokenCreate | None = None, ctx: WorkspaceContext = JwtWrite
):
    request.app.state.rate_limiter.check(
        f"extension:token:{client_ip(request)}:{ctx.user_id}",
        limit=10,
        window_seconds=60,
    )
    return await svc.create_token(ctx, body or s.ExtensionTokenCreate())


@router.get("/tokens", response_model=list[s.ExtensionTokenRead])
async def list_tokens(ctx: WorkspaceContext = JwtRead):
    return await svc.list_tokens(ctx)


@router.post("/tokens/{token_id}/revoke", status_code=204)
async def revoke_token(token_id: uuid.UUID, ctx: WorkspaceContext = JwtWrite):
    await svc.revoke_token(ctx, token_id)


@router.get("/session")
async def session_summary(ctx: WorkspaceContext = ExtRead) -> dict[str, Any]:
    return await svc.workspace_summary(ctx)


@router.get("/platform-policies", response_model=list[s.PlatformPolicyRead])
async def list_policies(ctx: WorkspaceContext = JwtRead):
    return await svc.list_policies(ctx)


@router.put("/platform-policies", response_model=s.PlatformPolicyRead)
async def put_policy(body: s.PlatformPolicyPut, ctx: WorkspaceContext = JwtManage):
    return await svc.put_policy(ctx, body)


@router.get("/platform-terms")
async def platform_terms(ctx: WorkspaceContext = JwtRead) -> dict[str, Any]:
    _ = ctx
    return {
        "restricted": sorted(RESTRICTED_PLATFORMS),
        "terms": PLATFORM_TERMS,
    }


@router.post("/clip", response_model=s.ClipResult, status_code=201)
async def clip(request: Request, body: s.ClipBody, ctx: WorkspaceContext = ExtWrite):
    request.app.state.rate_limiter.check(
        f"extension:clip:{ctx.workspace_id}:{ctx.user_id}",
        limit=60,
        window_seconds=60,
    )
    return await svc.clip_job(ctx, body)


@router.post("/runs/start", response_model=s.StartRunResult, status_code=201)
async def start_run(body: s.StartRunBody, ctx: WorkspaceContext = ExtWrite):
    return await svc.start_run(ctx, body)


@router.post("/runs/plan-page", response_model=s.PlanPageResult)
async def plan_page(request: Request, body: s.PlanPageBody, ctx: WorkspaceContext = ExtWrite):
    request.app.state.rate_limiter.check(
        f"extension:plan:{ctx.workspace_id}:{ctx.user_id}",
        limit=120,
        window_seconds=60,
    )
    return await svc.plan_page(ctx, body, storage=request.app.state.storage)


@router.post("/log-applied", status_code=201)
async def log_applied(body: s.LogAppliedBody, ctx: WorkspaceContext = ExtWrite) -> dict[str, Any]:
    return await svc.log_applied(ctx, body)


@router.post("/answer-insert", response_model=s.AnswerInsertResult)
async def answer_insert(body: s.AnswerInsertBody, ctx: WorkspaceContext = ExtWrite):
    return await svc.answer_insert(ctx, body)
