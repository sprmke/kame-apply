"""Propose improve ops from critique + market insights; verify each op."""

from __future__ import annotations

from typing import Any

from app.resumes.content import ResumeContent, ResumeLine
from app.resumes.verify import verify_operation


def propose_improvements(
    content: ResumeContent,
    *,
    critique: dict[str, Any],
    insights: dict[str, Any] | None,
    facts: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return proposed changes (accepted by verifier only)."""
    proposals: list[dict[str, Any]] = []
    comparison = (insights or {}).get("comparison") or {}
    profile_skills = {
        str(s.get("name") or ""): str(s.get("id") or "")
        for s in (facts.get("skills") or [])
        if isinstance(s, dict) and s.get("name")
    }

    # Quick wins: skills in profile but not on resume
    for name in (comparison.get("have_not_shown") or [])[:8]:
        sid = profile_skills.get(name) or next(
            (profile_skills[k] for k in profile_skills if k.lower() == name.lower()),
            "",
        )
        if not sid:
            continue
        op = {
            "op": "add_to_skills",
            "path": "sections.skills",
            "before": "",
            "after": name,
            "reason": "Demanded skill you already have but have not shown on the resume",
            "evidence_refs": [sid],
        }
        vr = verify_operation(after_text=name, evidence_refs=[sid], facts=facts)
        if vr.ok:
            proposals.append(op)

    # Summary targeting — only from profile headline/summary (never invent role-only fluff)
    role = content.target_role or ""
    if role and (
        not content.summary or role.lower().split()[0] not in (content.summary.text or "").lower()
    ):
        refs = [str(facts["id"])] if facts.get("id") else []
        base = (facts.get("headline") or facts.get("summary") or "").strip()
        if refs and base:
            after = base if role.lower() in base.lower() else f"{role}. {base}".strip()
            vr = verify_operation(after_text=after, evidence_refs=refs, facts=facts)
            if vr.ok:
                proposals.append(
                    {
                        "op": "summary",
                        "path": "summary",
                        "before": content.summary.text if content.summary else "",
                        "after": after,
                        "reason": "Name the target role in the summary",
                        "evidence_refs": refs,
                    }
                )

    # Profile → resume propagation: rewrite lines when evidence bullet text drifted
    bullets_by_id = {
        str(b["id"]): str(b.get("text") or "")
        for b in (facts.get("bullets") or [])
        if isinstance(b, dict) and b.get("id")
    }
    for line in content.all_lines():
        if len(line.evidence_refs) != 1:
            continue
        bid = line.evidence_refs[0]
        fresh = bullets_by_id.get(bid)
        if fresh and fresh.strip() and fresh.strip() != line.text.strip():
            vr = verify_operation(after_text=fresh, evidence_refs=[bid], facts=facts)
            if vr.ok:
                proposals.append(
                    {
                        "op": "rewrite",
                        "path": f"line:{line.id}",
                        "before": line.text,
                        "after": fresh,
                        "reason": "Profile bullet updated; sync this resume line",
                        "evidence_refs": [bid],
                    }
                )

    # Reorder skills: put demanded skills first (no text invention)
    demanded = [s["name"] for s in (insights or {}).get("skills") or [] if s.get("name")]
    skill_sec = next((s for s in content.sections if s.kind == "skills"), None)
    if skill_sec and demanded:
        current = [line.text for line in skill_sec.lines]
        ordered = sorted(
            current,
            key=lambda n: next(
                (i for i, d in enumerate(demanded) if d.lower() == n.lower()),
                999,
            ),
        )
        if ordered != current:
            proposals.append(
                {
                    "op": "reorder_skills",
                    "path": "sections.skills",
                    "before": ", ".join(current),
                    "after": ", ".join(ordered),
                    "reason": "Lead with skills most demanded in this Track",
                    "evidence_refs": [profile_skills[n] for n in ordered if n in profile_skills][
                        :20
                    ],
                }
            )

    # Critique-driven gaps become ask-for-metric prompts, not fabrications
    for fix in (critique.get("top_fixes") or [])[:5]:
        if fix.get("category") == "evidence" and "Quantify" in str(fix.get("message") or ""):
            proposals.append(
                {
                    "op": "ask_metric",
                    "path": f"line:{fix.get('line_id') or ''}",
                    "before": "",
                    "after": "",
                    "reason": fix["message"],
                    "evidence_refs": [],
                    "ask": "How many users, dollars, or percent impact can you confirm for this bullet?",
                }
            )

    return proposals


def apply_accepted_changes(
    content: ResumeContent,
    changes: list[dict[str, Any]],
) -> ResumeContent:
    data = content.model_copy(deep=True)
    for ch in changes:
        if ch.get("status") and ch["status"] != "accepted":
            continue
        op = ch.get("op")
        if op == "summary" and ch.get("after"):
            refs = [str(r) for r in (ch.get("evidence_refs") or [])]
            data.summary = ResumeLine(text=ch["after"], evidence_refs=refs)
        elif op == "add_to_skills" and ch.get("after"):
            skill_sec = next((s for s in data.sections if s.kind == "skills"), None)
            if skill_sec is None:
                from app.resumes.content import ResumeSection

                skill_sec = ResumeSection(kind="skills", heading="Skills", lines=[])
                data.sections.append(skill_sec)
            refs = [str(r) for r in (ch.get("evidence_refs") or [])]
            if not any(line.text.lower() == ch["after"].lower() for line in skill_sec.lines):
                skill_sec.lines.append(ResumeLine(text=ch["after"], evidence_refs=refs))
        elif op == "reorder_skills" and ch.get("after"):
            skill_sec = next((s for s in data.sections if s.kind == "skills"), None)
            if skill_sec:
                order = [x.strip() for x in ch["after"].split(",") if x.strip()]
                by_name = {line.text.lower(): line for line in skill_sec.lines}
                ordered_names = {n.lower() for n in order}
                skill_sec.lines = [by_name[n.lower()] for n in order if n.lower() in by_name] + [
                    line for line in skill_sec.lines if line.text.lower() not in ordered_names
                ]
        elif op == "rewrite" and ch.get("after") and str(ch.get("path") or "").startswith("line:"):
            line_id = str(ch["path"]).split(":", 1)[1]
            refs = [str(r) for r in (ch.get("evidence_refs") or [])]
            for line in data.all_lines():
                if line.id == line_id:
                    line.text = ch["after"]
                    line.evidence_refs = refs
                    line.unverified = False
                    break
    return data
