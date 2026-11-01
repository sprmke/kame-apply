import uuid

from fastapi import APIRouter, Depends, Request

from app.ai import service
from app.ai.providers import PROVIDERS
from app.ai.schemas import (
    AiSettingsRead,
    AiSettingsUpdate,
    CredentialCreate,
    CredentialRead,
    CredentialTestRead,
    OkRead,
    ProviderRead,
    UsageRead,
)
from app.core.security import WorkspaceContext, require_action

router = APIRouter(prefix="/ai", tags=["ai"])


def _cred(c) -> CredentialRead:
    return CredentialRead(
        id=c.id,
        provider=c.provider,
        label=c.label,
        key_hint=c.key_hint,
        base_url=c.base_url,
        status=c.status,
        last_tested_at=c.last_tested_at,
        created_at=c.created_at,
    )


@router.get("/providers", response_model=list[ProviderRead])
async def list_providers(_: WorkspaceContext = Depends(require_action("ai_credentials.read"))):
    return [
        ProviderRead(id=s.id, label=s.label, needs_key=s.needs_key, tier_models=s.tier_models)
        for s in PROVIDERS.values()
    ]


@router.get("/credentials", response_model=list[CredentialRead])
async def list_credentials(ctx: WorkspaceContext = Depends(require_action("ai_credentials.read"))):
    return [_cred(c) for c in await service.list_credentials(ctx)]


@router.post("/credentials", response_model=CredentialRead, status_code=201)
async def add_credential(
    body: CredentialCreate,
    request: Request,
    ctx: WorkspaceContext = Depends(require_action("ai_credentials.manage")),
):
    cred = await service.add_credential(
        ctx,
        request.app.state.settings,
        provider=body.provider,
        api_key=body.api_key.get_secret_value() if body.api_key else None,
        label=body.label,
        base_url=body.base_url,
    )
    return _cred(cred)


@router.delete("/credentials/{credential_id}", response_model=OkRead)
async def delete_credential(
    credential_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(require_action("ai_credentials.manage")),
):
    await service.delete_credential(ctx, credential_id)
    return OkRead()


@router.post("/credentials/{credential_id}/test", response_model=CredentialTestRead)
async def test_credential(
    credential_id: uuid.UUID,
    request: Request,
    ctx: WorkspaceContext = Depends(require_action("ai_credentials.manage")),
):
    limiter = request.app.state.rate_limiter
    if request.app.state.settings.auth_rate_limit_enabled:
        limiter.check(f"ai-test:ws:{ctx.workspace_id}", limit=20, window_seconds=3600)
    status, detail = await service.test_credential(
        ctx,
        request.app.state.settings,
        credential_id,
        model_factory=request.app.state.model_factory,
    )
    return CredentialTestRead(status=status, detail=detail)


@router.get("/settings", response_model=AiSettingsRead)
async def get_ai_settings(ctx: WorkspaceContext = Depends(require_action("ai_credentials.read"))):
    row = await service.get_settings(ctx)
    return AiSettingsRead(
        monthly_budget_cents=row.monthly_budget_cents,
        tier_models=row.tier_models,
        fallback_enabled=row.fallback_enabled,
    )


@router.patch("/settings", response_model=AiSettingsRead)
async def update_ai_settings(
    body: AiSettingsUpdate,
    ctx: WorkspaceContext = Depends(require_action("ai_credentials.manage")),
):
    row = await service.update_settings(
        ctx,
        monthly_budget_cents=body.monthly_budget_cents,
        tier_models=(
            {k: v.model_dump() for k, v in body.tier_models.items()}
            if body.tier_models is not None
            else None
        ),
        fallback_enabled=body.fallback_enabled,
    )
    return AiSettingsRead(
        monthly_budget_cents=row.monthly_budget_cents,
        tier_models=row.tier_models,
        fallback_enabled=row.fallback_enabled,
    )


@router.get("/usage", response_model=UsageRead)
async def get_usage(ctx: WorkspaceContext = Depends(require_action("ai_usage.read"))):
    return UsageRead(**await service.usage_summary(ctx))
