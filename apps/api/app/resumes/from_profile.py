"""Build a truthful base ResumeContent from Career Profile facts."""

from __future__ import annotations

from typing import Any

from app.resumes.content import (
    ContactBlock,
    ResumeContent,
    ResumeItem,
    ResumeLine,
    ResumeSection,
)


def build_from_profile(
    profile: dict[str, Any],
    *,
    target_role: str | None = None,
) -> ResumeContent:
    contact = ContactBlock(
        full_name=str(profile.get("display_name") or profile.get("full_name") or "Candidate"),
        email=profile.get("email"),
        phone=profile.get("phone"),
        location=profile.get("location") or profile.get("city"),
        links=[u for u in (profile.get("links") or []) if u][:5],
    )
    # The target role may label the document, but it is never presented as the candidate's own
    # headline or summary: that would be a claim with no profile evidence.
    headline = profile.get("headline")
    summary = None
    if profile.get("summary") or headline:
        text = str(profile.get("summary") or headline or "").strip()
        if text:
            # Summary evidence: profile id itself when no dedicated summary fact
            refs = [str(profile["id"])] if profile.get("id") else []
            summary = ResumeLine(text=text, evidence_refs=refs)

    sections: list[ResumeSection] = []

    exp_items: list[ResumeItem] = []
    bullets_by_exp: dict[str, list[dict[str, Any]]] = {}
    for b in profile.get("bullets") or []:
        eid = str(b.get("experience_id") or "")
        if eid:
            bullets_by_exp.setdefault(eid, []).append(b)

    for exp in profile.get("experiences") or []:
        eid = str(exp.get("id") or "")
        lines = []
        for b in bullets_by_exp.get(eid, []):
            lines.append(
                ResumeLine(
                    text=str(b.get("text") or ""),
                    evidence_refs=[str(b["id"])] if b.get("id") else ([eid] if eid else []),
                )
            )
        if not lines and exp.get("description"):
            lines.append(
                ResumeLine(
                    text=str(exp["description"]),
                    evidence_refs=[eid] if eid else [],
                )
            )
        exp_items.append(
            ResumeItem(
                id=eid or ResumeItem().id,
                title=str(exp.get("title") or ""),
                subtitle=str(exp.get("company") or "") or None,
                location=exp.get("location"),
                start=_fmt_date(exp.get("start_date")),
                end=_fmt_date(exp.get("end_date")),
                is_current=bool(exp.get("is_current")),
                lines=lines,
                evidence_refs=[eid] if eid else [],
            )
        )
    if exp_items:
        sections.append(ResumeSection(kind="experience", heading="Experience", items=exp_items))

    skill_lines = [
        ResumeLine(
            text=str(s.get("name") or ""),
            evidence_refs=[str(s["id"])] if s.get("id") else [],
        )
        for s in (profile.get("skills") or [])
        if s.get("name")
    ]
    if skill_lines:
        sections.append(ResumeSection(kind="skills", heading="Skills", lines=skill_lines))

    edu_items = []
    for ed in profile.get("education") or []:
        eid = str(ed.get("id") or "")
        title = str(ed.get("degree") or ed.get("field") or "Education")
        edu_items.append(
            ResumeItem(
                id=eid or ResumeItem().id,
                title=title,
                subtitle=str(ed.get("institution") or "") or None,
                start=_fmt_date(ed.get("start_date")),
                end=_fmt_date(ed.get("end_date")),
                lines=[],
                evidence_refs=[eid] if eid else [],
            )
        )
    if edu_items:
        sections.append(ResumeSection(kind="education", heading="Education", items=edu_items))

    return ResumeContent(
        contact=contact,
        summary=summary,
        sections=sections,
        target_role=target_role or (str(headline) if headline else None),
    )


def _fmt_date(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value)
    return s[:7] if len(s) >= 7 else s
