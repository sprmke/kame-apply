"""Compare pasted LinkedIn text against Career Profile facts."""

from __future__ import annotations

import re
from typing import Any

from app.strategy.schemas import ConsistencyIssue, ConsistencyReport

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", (s or "").lower()).strip()


def check_consistency(
    *,
    linkedin_text: str,
    experiences: list[dict[str, Any]],
    skills: list[str],
    display_name: str | None,
    headline: str | None,
) -> ConsistencyReport:
    text = linkedin_text or ""
    low = _norm(text)
    issues: list[ConsistencyIssue] = []

    if display_name and _norm(display_name) not in low:
        issues.append(
            ConsistencyIssue(
                field="name",
                severity="warn",
                message="Display name not found in LinkedIn paste",
                fix=f"Use the same name as Career Profile ({display_name})",
            )
        )

    for ex in experiences[:8]:
        company = str(ex.get("company") or "").strip()
        title = str(ex.get("title") or "").strip()
        if company and _norm(company) not in low:
            issues.append(
                ConsistencyIssue(
                    field="company",
                    severity="error",
                    message=f"Company missing on LinkedIn: {company}",
                    fix=f"Add {company} to Experience on LinkedIn",
                )
            )
        if title and _norm(title) not in low:
            issues.append(
                ConsistencyIssue(
                    field="title",
                    severity="warn",
                    message=f"Title wording differs or missing: {title}",
                    fix=f"Align LinkedIn title with Career Profile ({title})",
                )
            )
        start = ex.get("start_date")
        if start:
            year = str(start)[:4]
            if year.isdigit() and year not in text:
                issues.append(
                    ConsistencyIssue(
                        field="dates",
                        severity="info",
                        message=f"Start year {year} for {company or title} not visible in paste",
                        fix="Confirm dates match on LinkedIn",
                    )
                )

    missing_skills = [s for s in skills[:15] if s and _norm(s) not in low]
    for s in missing_skills[:5]:
        issues.append(
            ConsistencyIssue(
                field="skills",
                severity="info",
                message=f"Skill not found in LinkedIn paste: {s}",
                fix=f"Add {s} to LinkedIn Skills if you want recruiters to find it",
            )
        )

    # Fabrication sniff: LinkedIn claims companies not in profile
    for m in re.finditer(r"(?:at|@)\s+([A-Z][A-Za-z0-9&.\- ]{2,40})", text):
        claimed = m.group(1).strip()
        if len(claimed) < 3:
            continue
        if any(_norm(claimed) in _norm(str(ex.get("company") or "")) for ex in experiences):
            continue
        if any(_norm(str(ex.get("company") or "")) in _norm(claimed) for ex in experiences):
            continue
        # skip common words
        if _norm(claimed) in {"the", "linkedin", "inc", "llc"}:
            continue
        issues.append(
            ConsistencyIssue(
                field="company",
                severity="error",
                message=f"LinkedIn mentions company not in Career Profile: {claimed}",
                fix="Remove or add the role to Career Profile first (truthful only)",
            )
        )

    errors = sum(1 for i in issues if i.severity == "error")
    warns = sum(1 for i in issues if i.severity == "warn")
    score = max(0, 100 - errors * 20 - warns * 8 - max(0, len(issues) - errors - warns) * 2)
    return ConsistencyReport(issues=issues[:40], score=score)
