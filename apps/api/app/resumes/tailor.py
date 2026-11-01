"""Per-job tailor planner + deterministic drafter (research/05 §6)."""

from __future__ import annotations

from typing import Any

from app.resumes.content import ResumeContent, ResumeLine
from app.resumes.lens import run_lens
from app.resumes.stuffing import enforce_stuffing_caps, length_budget_trim
from app.resumes.verify import verify_content, verify_operation


def plan_tailor_ops(
    content: ResumeContent,
    *,
    lens_before: dict[str, Any],
    facts: dict[str, Any],
    qualifications: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (proposals that pass verifier, gaps that must not be invented)."""
    proposals: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    profile_skills = {
        str(s.get("name") or ""): str(s.get("id") or "")
        for s in (facts.get("skills") or [])
        if isinstance(s, dict) and s.get("name")
    }
    bullets = [b for b in (facts.get("bullets") or []) if isinstance(b, dict) and b.get("text")]
    resume_text = content.plain_text().lower()

    must_terms: list[str] = []
    for row in lens_before.get("qualifications") or []:
        kind = row.get("kind")
        verdict = row.get("verdict")
        text = str(row.get("text") or "")
        quote = str(row.get("quote") or text)
        n_name = ""
        for q in qualifications:
            if str(q.get("id") or "") == str(row.get("qual_id") or ""):
                n_name = str((q.get("normalized") or {}).get("name") or "")
                break
        surface = n_name or quote or text
        if kind == "must" and n_name:
            must_terms.append(n_name)

        if verdict in {"met"}:
            continue
        if verdict == "not_evidenced" and row.get("gap_option") == "surface":
            # Have in profile, not on resume → add skill / rewrite
            sid = profile_skills.get(n_name) or next(
                (profile_skills[k] for k in profile_skills if k.lower() == n_name.lower()),
                "",
            )
            if sid and n_name:
                op = {
                    "op": "add_to_skills",
                    "path": "sections.skills",
                    "before": "",
                    "after": n_name,  # posting surface form
                    "reason": f"Surface must-have '{n_name}' already in your profile",
                    "evidence_refs": [sid],
                    "qual_id": row.get("qual_id"),
                }
                if verify_operation(after_text=n_name, evidence_refs=[sid], facts=facts).ok:
                    proposals.append(op)
            # Also try to mention in a recent bullet using posting terminology
            matched_bullet = _find_bullet_for_skill(bullets, n_name)
            if matched_bullet:
                after = _rewrite_with_term(matched_bullet["text"], surface)
                refs = [str(matched_bullet["id"])]
                if (
                    after != matched_bullet["text"]
                    and verify_operation(after_text=after, evidence_refs=refs, facts=facts).ok
                ):
                    # Find line id on resume if present
                    line_id = _line_id_for_bullet(content, matched_bullet["text"])
                    proposals.append(
                        {
                            "op": "rewrite",
                            "path": f"line:{line_id}" if line_id else "line:new",
                            "before": matched_bullet["text"],
                            "after": after,
                            "reason": f"Use posting terminology for '{surface}'",
                            "evidence_refs": refs,
                            "qual_id": row.get("qual_id"),
                            "bullet_id": matched_bullet["id"],
                        }
                    )
            continue

        if verdict in {"not_evidenced", "not_met", "partial"}:
            # Adjacent: only bridge if profile has related skill
            adjacent = _adjacent_skill(n_name or surface, profile_skills)
            if adjacent and verdict == "partial":
                gaps.append(
                    {
                        "qual_id": row.get("qual_id"),
                        "text": text,
                        "option": "adjacent",
                        "message": (
                            f"You have related evidence ('{adjacent}'). "
                            "Confirm an honest bridge before we phrase it."
                        ),
                    }
                )
            elif row.get("gap_option") == "surface":
                pass
            else:
                gaps.append(
                    {
                        "qual_id": row.get("qual_id"),
                        "text": text,
                        "option": "skip_or_add_fact",
                        "message": (
                            "No evidence in your profile. Add a true fact, "
                            "or consider skipping this job."
                        ),
                    }
                )

    # Summary: put top 3 must terms that we can evidence into summary from profile
    top_must = []
    for t in must_terms:
        if any(t.lower() == k.lower() for k in profile_skills) and t.lower() not in (
            content.summary.text.lower() if content.summary else ""
        ):
            top_must.append(t)
        if len(top_must) >= 3:
            break
    if top_must and facts.get("id"):
        base = (facts.get("headline") or facts.get("summary") or "").strip()
        if base:
            after = f"{base} ({', '.join(top_must)})"
            # Only if terms appear in profile blob (skills)
            refs = [
                str(facts["id"]),
                *[
                    profile_skills[k]
                    for k in profile_skills
                    if any(k.lower() == t.lower() for t in top_must)
                ][:3],
            ]
            # Only use skill names + headline already in the profile (no new claims)
            skill_blob = " ".join(profile_skills.keys()).lower()
            if all(t.lower() in skill_blob or t.lower() in base.lower() for t in top_must):
                # Prefer skill evidence refs so numbers/claims stay grounded
                skill_refs = [
                    profile_skills[k]
                    for k in profile_skills
                    if any(k.lower() == t.lower() for t in top_must)
                ][:5] or [str(facts["id"])]
                if verify_operation(
                    after_text=after, evidence_refs=skill_refs, facts=facts
                ).ok or not any(ch.isdigit() for ch in after):
                    # Digit-free summary built from known tokens is allowed with skill refs
                    proposals.append(
                        {
                            "op": "summary",
                            "path": "summary",
                            "before": content.summary.text if content.summary else "",
                            "after": after,
                            "reason": "Name top evidenced must-haves in the summary",
                            "evidence_refs": skill_refs,
                        }
                    )

    # Dedupe by (op, after)
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for p in proposals:
        key = f"{p.get('op')}:{p.get('after')}:{p.get('path')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    _ = resume_text
    return unique, gaps


def apply_tailor_ops(
    content: ResumeContent,
    proposals: list[dict[str, Any]],
    *,
    facts: dict[str, Any],
    posting_terms: list[str],
) -> tuple[ResumeContent, list[dict[str, Any]]]:
    """Apply accepted-style ops, verify, length trim, stuffing caps."""
    data = content.model_copy(deep=True)
    applied: list[dict[str, Any]] = []
    for p in proposals:
        op = p.get("op")
        if op == "summary" and p.get("after"):
            refs = [str(r) for r in (p.get("evidence_refs") or [])]
            data.summary = ResumeLine(text=p["after"], evidence_refs=refs)
            applied.append(p)
        elif op == "add_to_skills" and p.get("after"):
            skill_sec = next((s for s in data.sections if s.kind == "skills"), None)
            if skill_sec is None:
                from app.resumes.content import ResumeSection

                skill_sec = ResumeSection(kind="skills", heading="Skills", lines=[])
                data.sections.append(skill_sec)
            refs = [str(r) for r in (p.get("evidence_refs") or [])]
            if not any(line.text.lower() == p["after"].lower() for line in skill_sec.lines):
                skill_sec.lines.insert(0, ResumeLine(text=p["after"], evidence_refs=refs))
                applied.append(p)
        elif op == "rewrite" and p.get("after"):
            path = str(p.get("path") or "")
            refs = [str(r) for r in (p.get("evidence_refs") or [])]
            if path.startswith("line:") and path != "line:new":
                line_id = path.split(":", 1)[1]
                for line in data.all_lines():
                    if line.id == line_id:
                        line.text = p["after"]
                        line.evidence_refs = refs
                        applied.append(p)
                        break
            else:
                # Match by before text
                before = (p.get("before") or "").strip()
                for line in data.all_lines():
                    if before and line.text.strip() == before:
                        line.text = p["after"]
                        line.evidence_refs = refs
                        applied.append(p)
                        break
    data = length_budget_trim(data)
    data, _warnings = enforce_stuffing_caps(data, posting_terms=posting_terms)
    vr = verify_content(data, facts)
    if not vr.ok:
        # Strip failing lines rather than ship fabrications
        bad = {r["line_id"] for r in vr.rejected}
        if data.summary and data.summary.id in bad:
            data.summary = content.summary
        for sec in data.sections:
            sec.lines = [line for line in sec.lines if line.id not in bad]
            for item in sec.items:
                item.lines = [line for line in item.lines if line.id not in bad]
    return data, applied


def skeptical_review(
    content: ResumeContent,
    *,
    lens_after: dict[str, Any],
    lens_before: dict[str, Any],
) -> list[str]:
    """Fresh-context reviewer notes (deterministic stand-in for LLM skeptic)."""
    notes: list[str] = []
    from app.resumes.lens import grade_rank

    if grade_rank(lens_after.get("grade") or "D") < grade_rank(lens_before.get("grade") or "D"):
        notes.append("Grade decreased after tailor; prefer the stronger version")
    auth = lens_after.get("authenticity") or {}
    if auth.get("banned_hits"):
        notes.append("Remove stock phrases flagged by authenticity check")
    skim = lens_after.get("skim") or {}
    if skim.get("missing_in_zone"):
        notes.append(
            "Top must-haves still missing from the 7-second zone: "
            + ", ".join(skim["missing_in_zone"][:3])
        )
    return notes


def _find_bullet_for_skill(bullets: list[dict[str, Any]], skill: str) -> dict[str, Any] | None:
    if not skill:
        return None
    low = skill.lower()
    for b in bullets:
        text = str(b.get("text") or "").lower()
        skills = [str(s).lower() for s in (b.get("skills") or [])]
        if low in text or any(low in s or s in low for s in skills):
            return b
    # Fallback: first strong bullet
    return bullets[0] if bullets else None


def _rewrite_with_term(text: str, term: str) -> str:
    if not term:
        return text
    if term.lower() in text.lower():
        return text
    # Append honest terminology without inventing metrics
    return f"{text.rstrip('.')} ({term})."


def _line_id_for_bullet(content: ResumeContent, bullet_text: str) -> str | None:
    target = bullet_text.strip().lower()
    for line in content.all_lines():
        if line.text.strip().lower() == target:
            return line.id
    return None


def _adjacent_skill(name: str, profile_skills: dict[str, str]) -> str | None:
    if not name:
        return None
    tokens = {t for t in name.lower().split() if len(t) > 2}
    for skill in profile_skills:
        st = {t for t in skill.lower().split() if len(t) > 2}
        if tokens & st:
            return skill
    return None


def tailor_once(
    content: ResumeContent,
    *,
    qualifications: list[dict[str, Any]],
    facts: dict[str, Any],
) -> dict[str, Any]:
    """Full deterministic tailor pass: lens → plan → apply → lens → review."""
    before = run_lens(content, qualifications=qualifications, facts=facts)
    proposals, gaps = plan_tailor_ops(
        content, lens_before=before, facts=facts, qualifications=qualifications
    )
    terms = [
        str((q.get("normalized") or {}).get("name") or q.get("quote") or "")
        for q in qualifications
        if q.get("kind") == "must"
    ]
    drafted, applied = apply_tailor_ops(
        content, proposals, facts=facts, posting_terms=[t for t in terms if t]
    )
    after = run_lens(drafted, qualifications=qualifications, facts=facts)
    review = skeptical_review(drafted, lens_after=after, lens_before=before)
    # One revise: if grade dropped, keep original content
    from app.resumes.lens import grade_rank

    final_content = drafted
    final_after = after
    if grade_rank(after.get("grade") or "D") < grade_rank(before.get("grade") or "D"):
        final_content = content
        final_after = before
        review = ["Kept base resume because tailor grade would have decreased", *review]
        applied = []

    return {
        "content": final_content,
        "lens_before": before,
        "lens_after": final_after,
        "proposals": proposals,
        "applied": applied,
        "gaps": gaps,
        "review": review,
        "knockouts": before.get("knockouts") or [],
    }
