"""AI credentials, settings, usage ledger, budget guard, and the single entry point for LLM calls.

Rules enforced here (docs/architecture, untrusted-content, truthful-content):
- Calls go through `run_text` only: tool-less, so untrusted text passed as `prompt` can never
  trigger an action. Callers must delimit untrusted content themselves.
- Every call is metered in `ai_usage` and checked against the monthly budget first.
- Plaintext provider keys live only in memory for the call and are never logged.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.ai import crypto
from app.ai.models import AiCredential, AiSettings, AiUsage, WorkspaceKey
from app.ai.providers import (
    PROVIDERS,
    TIERS,
    build_model,
    cost_micros,
    revalidate_base_url,
    validate_base_url,
)
from app.audit import service as audit
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.workspaces import limits

log = structlog.get_logger()

CALL_TIMEOUT_SECONDS = 60
MICROS_PER_CENT = 10_000


def _kek(settings: Settings) -> bytes:
    return crypto.parse_kek(settings.master_kek)


# --- keys ---------------------------------------------------------------------------------------


async def _dek(ctx: WorkspaceContext, settings: Settings, *, create: bool) -> bytes | None:
    row = await ctx.session.get(WorkspaceKey, ctx.workspace_id)
    if row is None:
        if not create:
            return None
        wrapped = crypto.new_wrapped_dek(_kek(settings), ctx.workspace_id)
        # Concurrent first saves race on the primary key; the loser re-reads the winner's row.
        await ctx.session.execute(
            pg_insert(WorkspaceKey)
            .values(workspace_id=ctx.workspace_id, wrapped_dek=wrapped)
            .on_conflict_do_nothing()
        )
        await ctx.session.flush()
        row = await ctx.session.get(WorkspaceKey, ctx.workspace_id, populate_existing=True)
        assert row is not None
    return crypto.unwrap_dek(_kek(settings), row.wrapped_dek, ctx.workspace_id)


# --- credentials --------------------------------------------------------------------------------


async def list_credentials(ctx: WorkspaceContext) -> list[AiCredential]:
    return list(
        (
            await ctx.session.execute(select(AiCredential).order_by(AiCredential.created_at))
        ).scalars()
    )


async def add_credential(
    ctx: WorkspaceContext,
    settings: Settings,
    *,
    provider: str,
    api_key: str | None,
    label: str | None,
    base_url: str | None,
) -> AiCredential:
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise AppError("unknown_provider", "Unknown provider", 422)
    if spec.needs_key and not api_key:
        raise AppError("key_required", "An API key is required for this provider", 422)
    if base_url and provider != "ollama":
        raise AppError("invalid_base_url", "Only Ollama accepts a custom URL", 422)
    if base_url:
        await revalidate_base_url(base_url, allow_private=not settings.is_prod)
        base_url = validate_base_url(base_url, allow_private=not settings.is_prod)
    count = (await ctx.session.execute(select(func.count()).select_from(AiCredential))).scalar_one()
    await limits.require_below(
        ctx.session, ctx.workspace_id, "max_ai_credentials", count, "credential_limit"
    )
    encrypted = hint = None
    if api_key:
        dek = await _dek(ctx, settings, create=True)
        assert dek is not None
        encrypted = crypto.encrypt_secret(dek, api_key, ctx.workspace_id)
        hint = api_key[-4:]
    cred = AiCredential(
        workspace_id=ctx.workspace_id,
        provider=provider,
        label=label,
        encrypted_key=encrypted,
        key_hint=hint,
        base_url=base_url,
        created_by=ctx.user_id,
    )
    ctx.session.add(cred)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="ai_credential.added",
        target_type="ai_credential",
        target_id=str(cred.id),
        after={"provider": provider},
    )
    return cred


async def _get_credential(ctx: WorkspaceContext, credential_id: uuid.UUID) -> AiCredential:
    cred = await ctx.session.get(AiCredential, credential_id)
    if cred is None:
        raise AppError("credential_not_found", "Credential not found", 404)
    return cred


async def delete_credential(ctx: WorkspaceContext, credential_id: uuid.UUID) -> None:
    cred = await _get_credential(ctx, credential_id)
    await ctx.session.delete(cred)
    await audit.record(
        ctx,
        action="ai_credential.deleted",
        target_type="ai_credential",
        target_id=str(credential_id),
        before={"provider": cred.provider},
    )


# --- settings -----------------------------------------------------------------------------------


async def get_settings(ctx: WorkspaceContext) -> AiSettings:
    row = await ctx.session.get(AiSettings, ctx.workspace_id)
    if row is None:
        await ctx.session.execute(
            pg_insert(AiSettings).values(workspace_id=ctx.workspace_id).on_conflict_do_nothing()
        )
        await ctx.session.flush()
        row = await ctx.session.get(AiSettings, ctx.workspace_id, populate_existing=True)
        assert row is not None
    return row


async def update_settings(
    ctx: WorkspaceContext,
    *,
    monthly_budget_cents: int | None,
    tier_models: dict[str, dict[str, str]] | None,
    fallback_enabled: bool | None,
) -> AiSettings:
    row = await get_settings(ctx)
    if monthly_budget_cents is not None:
        cap = (await limits.get_limits(ctx.session, ctx.workspace_id))["max_ai_budget_cents"]
        if monthly_budget_cents > cap:
            raise AppError(
                "budget_above_limit", "Budget is above this workspace's limit", 422, {"cap": cap}
            )
    before = {"monthly_budget_cents": row.monthly_budget_cents, "fallback": row.fallback_enabled}
    if monthly_budget_cents is not None:
        row.monthly_budget_cents = monthly_budget_cents
    if fallback_enabled is not None:
        row.fallback_enabled = fallback_enabled
    if tier_models is not None:
        for tier, choice in tier_models.items():
            if (
                tier not in TIERS
                or choice.get("provider") not in PROVIDERS
                or not choice.get("model")
            ):
                raise AppError("invalid_tier_models", "Unknown tier or provider", 422)
        row.tier_models = {
            t: {"provider": c["provider"], "model": c["model"]} for t, c in tier_models.items()
        }
    row.updated_at = datetime.now(UTC)
    await audit.record(
        ctx,
        action="ai_settings.updated",
        target_type="workspace",
        target_id=str(ctx.workspace_id),
        before=before,
        after={
            "monthly_budget_cents": row.monthly_budget_cents,
            "fallback": row.fallback_enabled,
            "tier_models": row.tier_models,
        },
    )
    return row


# --- usage and budget ---------------------------------------------------------------------------


def month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def month_spend_micros(ctx: WorkspaceContext) -> int:
    return int(
        (
            await ctx.session.execute(
                select(func.coalesce(func.sum(AiUsage.cost_micros), 0)).where(
                    AiUsage.created_at >= month_start()
                )
            )
        ).scalar_one()
    )


async def check_budget(ctx: WorkspaceContext, estimate_micros: int) -> None:
    """Hard stop before the call. A workflow that hits this pauses with a `budget` reason."""
    row = await get_settings(ctx)
    spent = await month_spend_micros(ctx)
    cap = row.monthly_budget_cents * MICROS_PER_CENT
    if spent + estimate_micros > cap:
        raise AppError(
            "budget_reached",
            "AI budget reached for this month",
            402,
            {"spent_cents": spent // MICROS_PER_CENT, "budget_cents": row.monthly_budget_cents},
        )


async def usage_summary(ctx: WorkspaceContext) -> dict[str, Any]:
    row = await get_settings(ctx)
    since = month_start()
    day = func.date_trunc("day", AiUsage.created_at)
    by_day = (
        await ctx.session.execute(
            select(day, func.sum(AiUsage.cost_micros), func.count())
            .where(AiUsage.created_at >= since)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    by_feature = (
        await ctx.session.execute(
            select(AiUsage.feature, func.sum(AiUsage.cost_micros), func.count())
            .where(AiUsage.created_at >= since)
            .group_by(AiUsage.feature)
            .order_by(func.sum(AiUsage.cost_micros).desc())
        )
    ).all()
    spent = sum(int(r[1]) for r in by_day)
    return {
        "month_start": since,
        "budget_cents": row.monthly_budget_cents,
        "spent_micros": spent,
        "by_day": [{"day": d, "cost_micros": int(c), "calls": n} for d, c, n in by_day],
        "by_feature": [{"feature": f, "cost_micros": int(c), "calls": n} for f, c, n in by_feature],
    }


# --- calling models -----------------------------------------------------------------------------


@dataclass(frozen=True)
class AiResult:
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_micros: int


@dataclass(frozen=True)
class StructuredAiResult:
    """Validated Pydantic output from a tool-less structured call."""

    output: Any
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_micros: int


def _is_auth_failure(e: ModelHTTPError) -> bool:
    if e.status_code in (401, 403):
        return True
    # Gemini answers 400 API_KEY_INVALID for a bad key.
    return e.status_code == 400 and "api_key_invalid" in str(e.body).lower().replace(" ", "_")


def _estimate(provider: str, model: str, system: str, prompt: str, max_out: int) -> int:
    approx_in = (len(system) + len(prompt)) // 3 + 1  # pessimistic chars-per-token
    return cost_micros(provider, model, approx_in, max_out)


async def _candidates(ctx: WorkspaceContext, *, tier: str) -> list[tuple[AiCredential, str]]:
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier}")
    cfg = await get_settings(ctx)
    creds = [c for c in await list_credentials(ctx) if c.status != "invalid"]
    if not creds:
        raise AppError("ai_not_configured", "Add an AI provider key to use this feature", 409)

    mapped = cfg.tier_models.get(tier)
    primary_provider = mapped["provider"] if mapped else creds[0].provider
    out: list[tuple[AiCredential, str]] = []
    for c in creds:
        if c.provider == primary_provider:
            model = mapped["model"] if mapped else PROVIDERS[c.provider].tier_models[tier]
            out.append((c, model))
            break
    if cfg.fallback_enabled or not out:
        seen = {c.id for c, _ in out}
        for c in creds:
            if c.id not in seen and c.provider != primary_provider and c.status == "valid":
                out.append((c, PROVIDERS[c.provider].tier_models[tier]))
    if not out:
        raise AppError("ai_not_configured", "No key is configured for this tier", 409)
    if not cfg.fallback_enabled:
        out = out[:1]
    return out


async def _invoke(
    ctx: WorkspaceContext,
    settings: Settings,
    cred: AiCredential,
    *,
    model_name: str,
    tier: str,
    feature: str,
    system: str,
    prompt: str,
    max_out: int,
    model_factory,
    output_type: type | None = None,
    retries: int = 0,
) -> tuple[Any, int, int, int]:
    api_key = None
    if cred.encrypted_key:
        dek = await _dek(ctx, settings, create=False)
        if dek is None:
            raise AppError("decryption_failed", "Stored credential could not be decrypted", 500)
        api_key = crypto.decrypt_secret(dek, cred.encrypted_key, ctx.workspace_id)
    if cred.base_url:
        await revalidate_base_url(cred.base_url, allow_private=not settings.is_prod)
    model = model_factory(cred.provider, api_key=api_key, model=model_name, base_url=cred.base_url)
    # No tools: untrusted text in `prompt` cannot trigger actions.
    agent_kwargs: dict[str, Any] = {"system_prompt": system}
    if output_type is not None:
        agent_kwargs["output_type"] = output_type
        agent_kwargs["retries"] = retries
    agent = Agent(model, **agent_kwargs)
    try:
        run = await asyncio.wait_for(
            agent.run(prompt, model_settings={"max_tokens": max_out}), CALL_TIMEOUT_SECONDS
        )
    except ModelHTTPError as e:
        if _is_auth_failure(e):
            cred.status = "invalid"
            cred.last_tested_at = datetime.now(UTC)
            await ctx.session.flush()
            raise AppError(
                "ai_credential_invalid", "The AI provider rejected this key", 409
            ) from None
        log.warning("ai_provider_http_error", provider=cred.provider, status=e.status_code)
        raise AppError("ai_provider_error", "The AI provider returned an error", 502) from None
    except TimeoutError:
        raise AppError("ai_provider_error", "The AI provider timed out", 504) from None
    except Exception as e:
        # Structured-output validation failures after retries surface here.
        name = type(e).__name__
        if output_type is not None and (
            "Validation" in name or "UnexpectedModelBehavior" in name or "AgentRun" in name
        ):
            log.warning("ai_structured_invalid", provider=cred.provider, error=name)
            raise AppError(
                "ai_output_invalid",
                "The model returned a draft that could not be validated",
                502,
            ) from None
        log.warning("ai_call_failed", provider=cred.provider, exc_info=True)
        raise AppError("ai_provider_error", "The AI provider call failed", 502) from None
    usage = run.usage
    in_t, out_t = usage.input_tokens or 0, usage.output_tokens or 0
    cost = cost_micros(cred.provider, model_name, in_t, out_t)
    ctx.session.add(
        AiUsage(
            workspace_id=ctx.workspace_id,
            credential_id=cred.id,
            provider=cred.provider,
            model=model_name,
            tier=tier,
            feature=feature,
            input_tokens=in_t,
            output_tokens=out_t,
            cost_micros=cost,
        )
    )
    await ctx.session.flush()
    return run.output, in_t, out_t, cost


async def run_text(
    ctx: WorkspaceContext,
    settings: Settings,
    *,
    tier: str,
    feature: str,
    system: str,
    prompt: str,
    max_output_tokens: int | None = None,
    model_factory=build_model,
) -> AiResult:
    """Run one tool-less text completion for a feature. Raises `ai_not_configured`,
    `budget_reached`, `ai_credential_invalid`, or `ai_provider_error`."""
    max_out = max_output_tokens or settings.ai_max_output_tokens
    candidates = await _candidates(ctx, tier=tier)
    last: AppError | None = None
    for cred, model_name in candidates:
        await check_budget(ctx, _estimate(cred.provider, model_name, system, prompt, max_out))
        try:
            output, in_t, out_t, cost = await _invoke(
                ctx,
                settings,
                cred,
                model_name=model_name,
                tier=tier,
                feature=feature,
                system=system,
                prompt=prompt,
                max_out=max_out,
                model_factory=model_factory,
            )
            return AiResult(str(output), cred.provider, model_name, in_t, out_t, cost)
        except AppError as e:
            if e.code != "ai_credential_invalid":
                raise
            last = e
    assert last is not None
    raise last


async def run_structured(
    ctx: WorkspaceContext,
    settings: Settings,
    *,
    tier: str,
    feature: str,
    system: str,
    prompt: str,
    output_type: type,
    max_output_tokens: int | None = None,
    model_factory=build_model,
    retries: int = 1,
) -> StructuredAiResult:
    """Tool-less structured completion. Validates against `output_type`, retries once by default,
    then fails with `ai_output_invalid`. Same budget and credential rules as `run_text`."""
    max_out = max_output_tokens or settings.ai_max_output_tokens
    candidates = await _candidates(ctx, tier=tier)
    last: AppError | None = None
    for cred, model_name in candidates:
        await check_budget(ctx, _estimate(cred.provider, model_name, system, prompt, max_out))
        try:
            output, in_t, out_t, cost = await _invoke(
                ctx,
                settings,
                cred,
                model_name=model_name,
                tier=tier,
                feature=feature,
                system=system,
                prompt=prompt,
                max_out=max_out,
                model_factory=model_factory,
                output_type=output_type,
                retries=retries,
            )
            return StructuredAiResult(output, cred.provider, model_name, in_t, out_t, cost)
        except AppError as e:
            if e.code != "ai_credential_invalid":
                raise
            last = e
    assert last is not None
    raise last


async def test_credential(
    ctx: WorkspaceContext,
    settings: Settings,
    credential_id: uuid.UUID,
    *,
    model_factory=build_model,
) -> tuple[str, str | None]:
    """Make one tiny call. Returns (status, detail) and records the outcome on the credential."""
    cred = await _get_credential(ctx, credential_id)
    model_name = PROVIDERS[cred.provider].tier_models["bulk"]
    status, detail = "valid", None
    try:
        await _invoke(
            ctx,
            settings,
            cred,
            model_name=model_name,
            tier="bulk",
            feature="credential_test",
            system="Reply with the single word: ok",
            prompt="ping",
            max_out=512,  # reasoning models spend tokens thinking first
            model_factory=model_factory,
        )
    except AppError as e:
        status = "invalid" if e.code == "ai_credential_invalid" else "error"
        detail = e.code
    if status != "error":
        cred.status = status
        cred.last_tested_at = datetime.now(UTC)
    await audit.record(
        ctx,
        action="ai_credential.tested",
        target_type="ai_credential",
        target_id=str(cred.id),
        after={"result": status},
    )
    return status, detail
