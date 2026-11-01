"""Deterministic interview prep from profile evidence + posting facts (truthful)."""

from __future__ import annotations

from typing import Any


def build_prep(
    *,
    company: str,
    title: str,
    job_description: str,
    skills: list[str],
    experiences: list[dict[str, Any]],
    bullets: list[dict[str, Any]],
) -> dict[str, Any]:
    company = (company or "the company").strip() or "the company"
    title = (title or "the role").strip() or "the role"
    skill_bits = [s for s in skills if s][:8]
    desc = (job_description or "")[:2000]

    brief_parts = [f"{title} at {company}."]
    if skill_bits:
        brief_parts.append("Posting skills to cover: " + ", ".join(skill_bits) + ".")
    if desc:
        brief_parts.append(
            "Ground answers in the posting text you already have; do not invent company facts."
        )
    company_brief = " ".join(brief_parts)

    questions: list[dict[str, str]] = [
        {"q": f"Why {company}?", "hint": "Use public facts you verified; leave gaps empty."},
        {
            "q": f"Walk me through a project relevant to {title}.",
            "hint": "Use a STAR story from your profile.",
        },
        {
            "q": "Tell me about a conflict or failure and what you changed.",
            "hint": "Only use real profile evidence.",
        },
    ]
    for sk in skill_bits[:4]:
        questions.append(
            {
                "q": f"How have you used {sk}?",
                "hint": "Cite a bullet or experience that mentions it, or say you have not.",
            }
        )

    stories: list[dict[str, str]] = []
    for exp in experiences[:5]:
        related = [
            b
            for b in bullets
            if b.get("experience_id") == exp.get("id") or not b.get("experience_id")
        ][:2]
        for b in related or [{"text": (exp.get("description") or "")[:240]}]:
            text = (b.get("text") or b.get("description") or "").strip()
            if not text:
                continue
            stories.append(
                {
                    "situation": f"{exp.get('title') or 'Role'} at {exp.get('company') or 'company'}",
                    "task": title,
                    "action": text[:400],
                    "result": "Use only outcomes already in your profile.",
                    "evidence_strength": str(b.get("evidence_strength") or "weak"),
                }
            )
            if len(stories) >= 5:
                break
        if len(stories) >= 5:
            break

    checklist = [
        {"item": "Review posting qualifications", "done": False},
        {"item": "Prepare 2 STAR stories from profile evidence", "done": False},
        {"item": "List questions for the interviewer", "done": False},
        {"item": "Confirm logistics (time zone, link)", "done": False},
    ]

    citations: list[dict[str, str]] = []
    if company:
        citations.append({"source": "application", "note": f"Company: {company}"})
    if title:
        citations.append({"source": "application", "note": f"Title: {title}"})
    for sk in skill_bits[:3]:
        citations.append({"source": "profile_skill", "note": sk})

    return {
        "company_brief": company_brief,
        "likely_questions": questions,
        "star_stories": stories,
        "checklist": checklist,
        "citations": citations,
    }
