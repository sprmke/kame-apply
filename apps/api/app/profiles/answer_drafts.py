"""Answer-bank drafts from profile facts (A3).

Reads only the profile and the existing bank. No writes, no AI, no sensitive fields.
Accepting a draft goes through the normal answer-bank endpoints, which audit the write.
"""

from __future__ import annotations

import uuid

from app.answers import bank_draft
from app.core.security import WorkspaceContext
from app.profiles import schemas as s
from app.profiles.answers import list_answers
from app.profiles.service import get_profile


async def draft_answers(
    ctx: WorkspaceContext, profile_id: uuid.UUID, body: s.AnswerDraftBody
) -> s.AnswerDraftBundle:
    profile = await get_profile(ctx, profile_id)
    rows = await list_answers(ctx, profile_id)
    existing = {(row.key, row.country) for row in rows}
    taken = set() if body.include_existing else existing

    items = bank_draft.draft_bank(
        {
            "display_name": profile.display_name,
            "headline": profile.headline,
            "location": profile.location,
            "work_authorization": dict(profile.work_authorization or {}),
            "salary_prefs": dict(profile.salary_prefs or {}),
            "links": list(profile.links or []),
        },
        existing=taken,
        keys=[k for k in (body.keys or []) if k] or None,
    )
    return s.AnswerDraftBundle(
        items=[s.AnswerDraftRead.model_validate(item) for item in items],
        existing=len(rows),
    )
