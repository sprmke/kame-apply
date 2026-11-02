"""Optional structured AI for the resume pipeline.

Every AI feature here is additive: with no key, no budget, or a provider failure, the caller keeps
its deterministic result. That keeps discovery, scoring, and the studio usable on a free tier.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.ai import service as ai
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext

log = logging.getLogger(__name__)

# Conditions where the deterministic path is the right answer, not an error.
SOFT_AI_ERRORS = frozenset(
    {
        "ai_not_configured",
        "budget_reached",
        "ai_provider_error",
        "ai_output_invalid",
        "ai_credential_invalid",
        "ssrf_blocked",
    }
)


class StructuredRunner(Protocol):
    async def __call__(self, ctx: WorkspaceContext, settings: Settings, **kwargs: Any) -> Any: ...


async def try_structured(
    ctx: WorkspaceContext,
    settings: Settings,
    *,
    tier: str,
    feature: str,
    system: str,
    prompt: str,
    output_type: Any,
    max_output_tokens: int | None = None,
    run_structured: StructuredRunner | None = None,
    model_factory: Any = None,
) -> Any | None:
    """Run a structured call, returning None when AI is unavailable. Never raises for soft stops."""
    runner = run_structured or ai.run_structured
    kwargs: dict[str, Any] = {
        "tier": tier,
        "feature": feature,
        "system": system,
        "prompt": prompt,
        "output_type": output_type,
    }
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens
    if model_factory is not None:
        kwargs["model_factory"] = model_factory
    try:
        return await runner(ctx, settings, **kwargs)
    except AppError as exc:
        if exc.code in SOFT_AI_ERRORS:
            log.info("ai_optional_skipped feature=%s code=%s", feature, exc.code)
            return None
        raise
