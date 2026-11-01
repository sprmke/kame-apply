"""Deterministic resume critique + optional LLM rubric (research/05 §3)."""

from __future__ import annotations

import re
from typing import Any

from app.resumes.content import ResumeContent
from app.resumes.verify import _BANNED

_PASSIVE = re.compile(r"\b(was|were|been|being)\s+\w+ed\b", re.I)
_QUANT = re.compile(r"\b\d")


def critique_resume(
    content: ResumeContent,
    *,
    market_skills: list[dict[str, Any]] | None = None,
    target_role: str | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    categories: dict[str, dict[str, Any]] = {}

    lines = content.all_lines()
    text_blob = "\n".join(line.text for line in lines)

    # Parseability (structure)
    parse_score = 5
    headings = [s.heading.lower() for s in content.sections]
    standard = {"experience", "education", "skills", "summary", "projects"}
    if not any(h in standard or h.rstrip("s") in standard for h in headings):
        parse_score -= 1
        findings.append(
            {
                "category": "parseability",
                "impact": 3,
                "message": "Use standard section headings (Experience, Skills, Education)",
                "line_id": None,
            }
        )
    if not content.contact.email and not content.contact.phone:
        parse_score -= 2
        findings.append(
            {
                "category": "parseability",
                "impact": 5,
                "message": "Add contact details in the header",
                "line_id": None,
            }
        )
    categories["parseability"] = {"score": max(0, parse_score), "max": 5}

    # Targeting
    target_score = 5
    role = (target_role or content.target_role or "").lower()
    if role and content.summary and role.split()[0] not in content.summary.text.lower():
        target_score -= 2
        findings.append(
            {
                "category": "targeting",
                "impact": 4,
                "message": "Summary should name the target role",
                "line_id": content.summary.id if content.summary else None,
            }
        )
    elif not content.summary:
        target_score -= 2
        findings.append(
            {
                "category": "targeting",
                "impact": 4,
                "message": "Add a short summary aimed at this Track",
                "line_id": None,
            }
        )
    categories["targeting"] = {"score": max(0, target_score), "max": 5}

    # Evidence & impact
    evidence_score = 5
    bullet_lines = [
        line
        for s in content.sections
        if s.kind == "experience"
        for it in s.items
        for line in it.lines
    ]
    if bullet_lines:
        quantified = sum(1 for line in bullet_lines if _QUANT.search(line.text))
        ratio = quantified / len(bullet_lines)
        if ratio < 0.3:
            evidence_score -= 2
            findings.append(
                {
                    "category": "evidence",
                    "impact": 4,
                    "message": "Quantify more bullets (scope, outcome, metrics from your profile)",
                    "line_id": bullet_lines[0].id,
                }
            )
        long_bullets = [line for line in bullet_lines if len(line.text) > 220]
        if long_bullets:
            evidence_score -= 1
            findings.append(
                {
                    "category": "evidence",
                    "impact": 2,
                    "message": "Keep bullets to about two lines",
                    "line_id": long_bullets[0].id,
                }
            )
    else:
        evidence_score -= 3
        findings.append(
            {
                "category": "evidence",
                "impact": 5,
                "message": "Add experience bullets with outcomes",
                "line_id": None,
            }
        )
    categories["evidence"] = {"score": max(0, evidence_score), "max": 5}

    # Market fit
    market_score = 5
    top = [s for s in (market_skills or [])[:15]]
    if top:
        shown = {line.text.lower() for line in lines}
        skill_names = {
            line.text.lower() for s in content.sections if s.kind == "skills" for line in s.lines
        }
        missing = []
        for s in top[:10]:
            name = str(s.get("name") or "").lower()
            if not name:
                continue
            if name not in skill_names and not any(name in t for t in shown):
                missing.append(name)
        if missing:
            market_score -= min(3, len(missing))
            findings.append(
                {
                    "category": "market_fit",
                    "impact": 5,
                    "message": f"Surface demanded skills you have: {', '.join(missing[:5])}",
                    "line_id": None,
                }
            )
    categories["market_fit"] = {"score": max(0, market_score), "max": 5}

    # Clarity
    clarity = 5
    if _PASSIVE.search(text_blob):
        clarity -= 1
        findings.append(
            {
                "category": "clarity",
                "impact": 2,
                "message": "Prefer active voice in bullets",
                "line_id": None,
            }
        )
    categories["clarity"] = {"score": max(0, clarity), "max": 5}

    # Authenticity
    auth = 5
    low = text_blob.lower()
    for phrase in _BANNED:
        if phrase in low:
            auth -= 2
            findings.append(
                {
                    "category": "authenticity",
                    "impact": 3,
                    "message": f'Remove stock phrase "{phrase}"',
                    "line_id": None,
                }
            )
    categories["authenticity"] = {"score": max(0, auth), "max": 5}

    # Consistency
    consistency = 5
    categories["consistency"] = {"score": consistency, "max": 5}

    # Human skim (top third)
    skim = 5
    if content.summary and len(content.summary.text) > 400:
        skim -= 1
        findings.append(
            {
                "category": "skim",
                "impact": 3,
                "message": "Tighten the summary for the 7-second skim zone",
                "line_id": content.summary.id,
            }
        )
    categories["skim"] = {"score": max(0, skim), "max": 5}

    findings.sort(key=lambda f: -int(f.get("impact") or 0))
    top_fixes = findings[:5]
    return {
        "categories": categories,
        "findings": findings,
        "top_fixes": top_fixes,
        "skim_zone": {
            "summary": content.summary.text if content.summary else "",
            "first_role": next(
                (
                    f"{it.title}, {it.subtitle}"
                    for s in content.sections
                    if s.kind == "experience"
                    for it in s.items[:1]
                ),
                "",
            ),
        },
    }
