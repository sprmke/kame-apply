"""Match a pasted employer reply to one of the workspace's applications (A5).

Rule-based, no AI, no ids. Workspace scoping is enforced by RLS plus an explicit
workspace filter. The email is untrusted data and is never used as an instruction.
"""

from __future__ import annotations

import re

from sqlalchemy import select

from app.applications.models import Application
from app.core.security import WorkspaceContext

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "and", "for", "with", "your", "our", "you", "are", "this", "that", "from"}


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").casefold()) if len(w) > 3 and w not in _STOP]


def _domain(sender: str) -> str:
    if "@" not in sender:
        return ""
    host = sender.rsplit("@", 1)[-1].casefold()
    return host.split(".")[0] if host else ""


async def match_application(
    ctx: WorkspaceContext,
    *,
    sender: str,
    subject: str,
    body_text: str,
) -> dict | None:
    text = f"{sender} {subject} {body_text}".casefold()
    if not text.strip():
        return None
    domain = _domain(sender)

    rows = (
        (
            await ctx.session.execute(
                select(Application)
                .where(Application.workspace_id == ctx.workspace_id)
                .order_by(Application.created_at.desc())
                .limit(500)
            )
        )
        .scalars()
        .all()
    )

    best: tuple[int, Application, list[str]] | None = None
    for row in rows:
        if row.status in {"withdrawn", "rejected"}:
            continue
        score = 0
        reasons: list[str] = []
        for token in _tokens(row.company_name or ""):
            if token in text:
                score += 3
                if "Company name in the email" not in reasons:
                    reasons.append("Company name in the email")
        for token in _tokens(row.job_title or ""):
            if token in text:
                score += 1
        if domain and domain in (row.company_name or "").casefold().replace(" ", ""):
            score += 2
            reasons.append("Sender matches the company")
        if domain and domain in text:
            score += 1
        if score and (best is None or score > best[0]):
            best = (score, row, reasons)

    if best is None:
        return None
    score, row, reasons = best
    if score < 3:
        return None
    return {
        "application_id": row.id,
        "job_title": row.job_title or "",
        "company_name": row.company_name or "",
        "score": min(1.0, score / 10),
        "reason": reasons[0] if reasons else "Words in the email match this application",
    }
