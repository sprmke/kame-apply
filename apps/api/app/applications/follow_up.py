"""Draft follow-up email text (copy-only; never auto-sent)."""

from __future__ import annotations


def draft_follow_up(*, company: str, title: str, user_name: str = "", day: int = 7) -> str:
    company = (company or "the team").strip()
    title = (title or "the role").strip()
    sign = (user_name or "").strip() or "Best regards"
    if day >= 14:
        body = (
            f"I applied for {title} at {company} about two weeks ago and wanted to check in. "
            f"I remain interested and can share references or a short work sample if useful."
        )
    else:
        body = (
            f"I applied for {title} at {company} about a week ago and wanted to follow up. "
            f"I remain very interested and am happy to share anything else that would help."
        )
    return f"Hello,\n\n{body}\n\n{sign}\n"
