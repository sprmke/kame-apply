"""LLM rubric enrichment for the resume critique (deterministic baseline + optional AI)."""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import PromptedOutput

from app.ai import prompts
from app.ai.optional import StructuredRunner, try_structured
from app.core.config import Settings
from app.core.security import WorkspaceContext
from app.resumes.content import ResumeContent
from app.safety.sanitize import for_ai_context

FEATURE = "resume_critique"
TIER = "standard"
MAX_OUT = 1200

# Categories the deterministic pass owns plus two the model can add.
ALLOWED_CATEGORIES = frozenset(
    {
        "parseability",
        "targeting",
        "evidence",
        "market_fit",
        "clarity",
        "authenticity",
        "consistency",
        "skim",
        "impact",
        "specificity",
    }
)


class AiCritiqueFinding(BaseModel):
    category: str = Field(max_length=40)
    message: str = Field(min_length=1, max_length=300)
    impact: int = Field(ge=1, le=5)
    line_id: str | None = None


class AiCritique(BaseModel):
    categories: dict[str, int] = Field(default_factory=dict)
    findings: list[AiCritiqueFinding] = Field(default_factory=list, max_length=15)
    summary: str = Field(default="", max_length=600)


def _prompt(
    content: ResumeContent,
    *,
    target_role: str | None,
    market_skills: list[dict[str, Any]] | None,
) -> str:
    bundle = for_ai_context(content.plain_text(), kind="resume")
    skills = ", ".join(str(s.get("name")) for s in (market_skills or [])[:15] if s.get("name"))
    return (
        f"Target role: {target_role or content.target_role or 'unspecified'}\n"
        f"Market skills for this Track: {skills or 'none provided'}\n"
        f"{bundle.delimited}\n"
        "Score each category 0-5: parseability, targeting, evidence, market_fit, clarity, "
        "authenticity, consistency, skim, impact, specificity. Report only what the resume "
        "actually contains. Every finding needs an impact 1-5 and, when it points at a line, "
        "the line_id from the resume. Never invent employers, metrics, or skills."
    )


def _merge(
    base: dict[str, Any],
    ai: AiCritique,
    *,
    provider: str,
    model: str,
    valid_line_ids: set[str],
) -> dict[str, Any]:
    out = copy.deepcopy(base)
    categories = dict(out.get("categories") or {})
    for name, raw in (ai.categories or {}).items():
        key = name.strip().lower()
        if key not in ALLOWED_CATEGORIES:
            continue
        try:
            score = max(0, min(5, int(raw)))
        except (TypeError, ValueError):
            continue
        if key in categories:
            # Keep the stricter of the two scores: the model must not paper over a known issue.
            categories[key] = {"score": min(int(categories[key]["score"]), score), "max": 5}
        else:
            categories[key] = {"score": score, "max": 5}

    findings = list(out.get("findings") or [])
    for f in ai.findings or []:
        category = f.category.strip().lower()[:40] or "general"
        line_id = f.line_id if f.line_id in valid_line_ids else None
        findings.append(
            {
                "category": category,
                "impact": max(1, min(5, int(f.impact))),
                "message": f.message.strip()[:300],
                "line_id": line_id,
                "source": "ai",
            }
        )
    findings.sort(key=lambda x: -int(x.get("impact") or 0))
    out["categories"] = categories
    out["findings"] = findings[:12]
    out["top_fixes"] = out["findings"][:5]
    out["ai"] = {"provider": provider, "model": model, "summary": ai.summary.strip()[:600]}
    return out


async def enrich_critique(
    ctx: WorkspaceContext,
    settings: Settings,
    *,
    report: dict[str, Any],
    content: ResumeContent,
    market_skills: list[dict[str, Any]] | None = None,
    target_role: str | None = None,
    run_structured: StructuredRunner | None = None,
    model_factory: Any = None,
) -> dict[str, Any]:
    """Add the LLM rubric on top of the deterministic report. Returns the base on any soft stop."""
    result = await try_structured(
        ctx,
        settings,
        tier=TIER,
        feature=FEATURE,
        system=prompts.RESUME_CRITIQUE.system,
        prompt=_prompt(content, target_role=target_role, market_skills=market_skills),
        output_type=PromptedOutput(AiCritique),
        max_output_tokens=MAX_OUT,
        run_structured=run_structured,
        model_factory=model_factory,
    )
    if result is None:
        return report
    valid_line_ids = {line.id for line in content.all_lines()}
    if content.summary:
        valid_line_ids.add(content.summary.id)
    return _merge(
        report,
        result.output,
        provider=result.provider,
        model=result.model,
        valid_line_ids=valid_line_ids,
    )
