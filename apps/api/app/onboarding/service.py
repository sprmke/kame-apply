"""One setup plan from a resume and a role sentence (A1).

Read-only: it returns a draft bundle the user reviews. Accepting happens through the normal
profile, answer, search, and schedule endpoints, each of which writes its own activity row.
"""

from __future__ import annotations

from typing import Any

from app.answers import bank_draft
from app.core.security import WorkspaceContext
from app.onboarding import schemas as s
from app.onboarding.parse import clean_text, parse_resume_text
from app.profiles.answers import list_answers
from app.profiles.service import get_profile
from app.tracks.plan import generate_plan


async def plan_onboarding(
    ctx: WorkspaceContext,
    settings: Any,
    body: s.OnboardingPlanBody,
    *,
    run_structured: Any = None,
) -> s.OnboardingPlanRead:
    basics = parse_resume_text(clean_text(body.resume_text or ""))

    answers: list[dict[str, Any]] = []
    if body.profile_id:
        import uuid

        try:
            profile_id = uuid.UUID(body.profile_id)
        except ValueError:
            profile_id = None
        if profile_id is not None:
            profile = await get_profile(ctx, profile_id)
            rows = await list_answers(ctx, profile_id)
            existing = {(row.key, row.country) for row in rows}
            answers = bank_draft.draft_bank(
                {
                    "display_name": profile.display_name,
                    "headline": profile.headline,
                    "location": profile.location,
                    "work_authorization": dict(profile.work_authorization or {}),
                    "salary_prefs": dict(profile.salary_prefs or {}),
                    "links": list(profile.links or []),
                },
                existing=existing,
            )

    search = None
    source: str = "defaults"
    if body.role_text and body.role_text.strip():
        plan = await generate_plan(
            ctx,
            settings,
            text=body.role_text.strip(),
            run_structured=run_structured,
        )
        source = "ai" if plan.get("source") == "ai" else "defaults"
        search = {
            "name": plan.get("name") or "",
            "criteria": plan.get("criteria"),
            "summary": plan.get("summary") or "",
            "source": plan.get("source") or "defaults",
            "ai_error": plan.get("ai_error"),
        }

    return s.OnboardingPlanRead(
        basics=s.ResumeBasics.model_validate(basics),
        answers=answers,
        search=search,
        schedule=s.ScheduleDefaults(timezone=body.timezone or "UTC"),
        source=source,
    )
