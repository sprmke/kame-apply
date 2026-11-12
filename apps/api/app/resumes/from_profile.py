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
    pack: Any = None,
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
        sections.append(
            ResumeSection(
                kind="experience",
                heading=_heading(pack, "experience", "Experience"),
                items=exp_items,
            )
        )

    skill_lines = [
        ResumeLine(
            text=str(s.get("name") or ""),
            evidence_refs=[str(s["id"])] if s.get("id") else [],
        )
        for s in (profile.get("skills") or [])
        if s.get("name")
    ]
    if skill_lines:
        sections.append(
            ResumeSection(
                kind="skills", heading=_heading(pack, "skills", "Skills"), lines=skill_lines
            )
        )

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
        sections.append(
            ResumeSection(
                kind="education", heading=_heading(pack, "education", "Education"), items=edu_items
            )
        )

    project_bullets: dict[str, list[dict[str, Any]]] = {}
    for b in profile.get("bullets") or []:
        pid = str(b.get("project_id") or "")
        if pid:
            project_bullets.setdefault(pid, []).append(b)
    project_items: list[ResumeItem] = []
    for project in profile.get("projects") or []:
        pid = str(project.get("id") or "")
        lines = [
            ResumeLine(
                text=str(b.get("text") or ""),
                evidence_refs=[str(b["id"])] if b.get("id") else ([pid] if pid else []),
            )
            for b in project_bullets.get(pid, [])
            if b.get("text")
        ]
        if not lines and project.get("description"):
            lines = [
                ResumeLine(
                    text=str(project["description"]),
                    evidence_refs=[pid] if pid else [],
                )
            ]
        project_items.append(
            ResumeItem(
                id=pid or ResumeItem().id,
                title=str(project.get("name") or "Project"),
                subtitle=str(project.get("url") or "") or None,
                start=_fmt_date(project.get("start_date")),
                end=_fmt_date(project.get("end_date")),
                lines=lines,
                evidence_refs=[pid] if pid else [],
            )
        )
    if project_items:
        sections.append(
            ResumeSection(
                kind="projects",
                heading=_heading(pack, "projects", "Projects"),
                items=project_items,
            )
        )

    cert_items: list[ResumeItem] = []
    for cert in profile.get("certifications") or []:
        cid = str(cert.get("id") or "")
        detail = " · ".join(
            part
            for part in (
                str(cert.get("issuer") or ""),
                str(cert.get("expires_on") or "")[:10] if cert.get("expires_on") else "",
            )
            if part
        )
        cert_items.append(
            ResumeItem(
                id=cid or ResumeItem().id,
                title=str(cert.get("name") or "Certification"),
                subtitle=detail or None,
                start=_fmt_date(cert.get("issued_on")),
                end=None,
                lines=[],
                evidence_refs=[cid] if cid else [],
            )
        )
    if cert_items:
        sections.append(
            ResumeSection(
                kind="certifications",
                heading=_heading(pack, "certifications", "Certifications"),
                items=cert_items,
            )
        )

    language_lines = [
        ResumeLine(
            text=str(lang.get("name") or ""),
            evidence_refs=[str(lang["id"])] if lang.get("id") else [],
        )
        for lang in profile.get("languages") or []
        if lang.get("name")
    ]
    if language_lines:
        sections.append(
            ResumeSection(
                kind="languages",
                heading=_heading(pack, "languages", "Languages"),
                lines=language_lines,
            )
        )

    if pack is not None and pack.resume.section_order:
        order = {kind: index for index, kind in enumerate(pack.resume.section_order)}
        sections.sort(key=lambda section: order.get(section.kind, 99))

    return ResumeContent(
        contact=contact,
        summary=summary,
        sections=sections,
        target_role=target_role or (str(headline) if headline else None),
    )


def _heading(pack: Any, kind: str, fallback: str) -> str:
    if pack is None:
        return fallback
    return pack.resume.section_titles.get(kind, fallback)


def _fmt_date(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value)
    return s[:7] if len(s) >= 7 else s
