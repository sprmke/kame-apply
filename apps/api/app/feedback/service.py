"""Submit beta feedback. Never includes profile/resume content or auth tokens."""

from __future__ import annotations

import httpx

from app.audit import service as audit
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext

ALLOWED = frozenset({"bug", "friction", "idea", "general"})


async def submit(
    ctx: WorkspaceContext,
    settings: Settings,
    *,
    category: str,
    message: str,
    page: str | None,
) -> str | None:
    cat = category.strip().lower() if category else "general"
    if cat not in ALLOWED:
        raise AppError("invalid_category", "Pick a valid feedback category", 422)

    body = (
        f"### Category\n{cat}\n\n"
        f"### Page\n{page or '(none)'}\n\n"
        f"### Message\n{message}\n\n"
        "---\n_Submitted via in-app feedback. No account email or profile data included._"
    )
    issue_url: str | None = None
    if settings.github_feedback_token:
        repo = settings.github_feedback_repo
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{repo}/issues",
                headers={
                    "Authorization": f"Bearer {settings.github_feedback_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={
                    "title": f"[beta/{cat}] {message[:72]}",
                    "body": body,
                    "labels": ["beta-feedback", cat],
                },
            )
        if resp.status_code >= 300:
            raise AppError("feedback_failed", "Could not file feedback right now", 502)
        issue_url = resp.json().get("html_url")

    await audit.record(
        ctx,
        action="feedback.submitted",
        target_type="feedback",
        target_id=None,
        after={"category": cat, "page": page, "has_github_issue": bool(issue_url)},
    )
    return issue_url
