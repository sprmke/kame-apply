"""Optional LLM skeptical review of a tailored draft (advisory notes only)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import PromptedOutput

from app.ai import prompts
from app.ai.optional import StructuredRunner, try_structured
from app.core.config import Settings
from app.core.security import WorkspaceContext
from app.resumes.content import ResumeContent
from app.safety.sanitize import for_ai_context

FEATURE = "resume_tailor_review"
TIER = "standard"
MAX_OUT = 800
MAX_NOTES = 5


class AiTailorReview(BaseModel):
    notes: list[str] = Field(default_factory=list, max_length=MAX_NOTES)


def _prompt(
    content: ResumeContent,
    *,
    qualifications: list[dict[str, Any]],
    deterministic_notes: list[str],
) -> str:
    bundle = for_ai_context(content.plain_text(), kind="resume")
    musts = [
        str(q.get("text") or (q.get("normalized") or {}).get("name") or "")
        for q in qualifications
        if q.get("kind") == "must"
    ][:15]
    return (
        f"Must-have requirements: {', '.join(m for m in musts if m) or 'none'}\n"
        f"Deterministic review notes: {'; '.join(deterministic_notes) or 'none'}\n"
        f"{bundle.delimited}\n"
        "Give at most three short, concrete fixes. Focus on keyword stuffing, missing must-haves "
        "in the top third, and claims that read as unsupported. Use only evidence already in the "
        "resume. Never suggest adding employers, metrics, or skills that are not present."
    )


async def review_tailored_draft(
    ctx: WorkspaceContext,
    settings: Settings,
    *,
    content: ResumeContent,
    qualifications: list[dict[str, Any]],
    deterministic_notes: list[str],
    run_structured: StructuredRunner | None = None,
    model_factory: Any = None,
) -> list[str]:
    """Return deterministic notes plus up to three advisory LLM notes. Never raises for soft stops."""
    result = await try_structured(
        ctx,
        settings,
        tier=TIER,
        feature=FEATURE,
        system=prompts.RESUME_TAILOR_REVIEW.system,
        prompt=_prompt(
            content, qualifications=qualifications, deterministic_notes=deterministic_notes
        ),
        output_type=PromptedOutput(AiTailorReview),
        max_output_tokens=MAX_OUT,
        run_structured=run_structured,
        model_factory=model_factory,
    )
    if result is None:
        return deterministic_notes
    notes = list(deterministic_notes)
    for note in result.output.notes[:3]:
        clean = str(note).strip()[:300]
        if clean and clean not in notes:
            notes.append(clean)
    return notes[:MAX_NOTES]
