"""Recruiter Lens: requirement-by-requirement Fit & Gap on what an ATS would see."""

from __future__ import annotations

from typing import Any

from app.matching.knockout import predict_knockouts
from app.matching.verdicts import verdict_for_qual
from app.profiles.banned_phrases import DEFAULT_BANNED_PHRASES
from app.resumes.content import ResumeContent
from app.resumes.render import parse_view
from app.resumes.verify import _BANNED

_GRADE_THRESHOLDS = (
    (0.90, "A"),
    (0.80, "A-"),
    (0.70, "B+"),
    (0.60, "B"),
    (0.50, "B-"),
    (0.40, "C+"),
    (0.30, "C"),
    (0.20, "C-"),
    (0.10, "D+"),
)


def _grade(score: float) -> str:
    for threshold, letter in _GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "D"


def _resume_skill_names(content: ResumeContent) -> set[str]:
    names: set[str] = set()
    blob = content.plain_text().lower()
    for sec in content.sections:
        if sec.kind == "skills":
            names.update(line.text.lower() for line in sec.lines)
    # Also surface skills mentioned in bullets
    for line in content.all_lines():
        names.add(line.text.lower())
    names.add(blob)
    return names


def _profile_skill_set(facts: dict[str, Any]) -> set[str]:
    return {
        str(s.get("name") or "").lower()
        for s in (facts.get("skills") or [])
        if isinstance(s, dict) and s.get("name")
    }


def _years_from_facts(facts: dict[str, Any]) -> float:
    years = 0.0
    for exp in facts.get("experiences") or []:
        if not isinstance(exp, dict):
            continue
        start = str(exp.get("start_date") or "")[:4]
        end = str(exp.get("end_date") or "")[:4]
        try:
            s_y = int(start) if start.isdigit() else 0
            e_y = int(end) if end.isdigit() else 2026
            if s_y:
                years += max(0, e_y - s_y)
        except ValueError:
            continue
    return float(years)


def run_lens(
    content: ResumeContent,
    *,
    qualifications: list[dict[str, Any]],
    facts: dict[str, Any],
    answers: dict[str, Any] | None = None,
    linkedin_text: str | None = None,
) -> dict[str, Any]:
    """Grade resume against job qualifications. Deterministic given fixed inputs."""
    answers = answers or {}
    parsed = parse_view(content)
    resume_text = content.plain_text().lower()
    profile_skills = _profile_skill_set(facts)
    resume_skills = _resume_skill_names(content)
    # For Lens, "shown" skills are those visible in the resume text / skills section
    shown_skills = {s for s in profile_skills if s and s in resume_text}
    years = _years_from_facts(facts)
    degrees = {
        str(e.get("degree") or e.get("field") or "").lower()
        for e in (facts.get("education") or [])
        if isinstance(e, dict)
    }
    degrees.discard("")
    languages: set[str] = set()
    for sec in content.sections:
        if sec.kind == "languages":
            languages.update(line.text.lower() for line in sec.lines)

    knockouts = predict_knockouts(
        qualifications,
        profile={
            "work_authorization": facts.get("work_authorization") or {},
            "years_experience": years,
            "degrees": list(degrees),
            "languages": list(languages),
            "licenses": [
                str(c.get("name") or "").lower()
                for c in (facts.get("certifications") or [])
                if isinstance(c, dict)
            ],
            "country": (facts.get("location") or "")[:2].upper() if facts.get("location") else "",
        },
        answers=answers,
    )
    ko_ids = {str(h.get("qual_id")) for h in knockouts if h.get("qual_id")}

    rows: list[dict[str, Any]] = []
    must_total = must_met = pref_total = pref_met = 0
    long_wishlist = sum(1 for q in qualifications if q.get("kind") in {"must", "preferred"}) >= 30

    for q in qualifications:
        qid = str(q.get("id") or "")
        kind = q.get("kind") or "preferred"
        v = verdict_for_qual(
            q,
            profile_skills=shown_skills or resume_skills,
            profile_years=years,
            profile_degrees=degrees,
            profile_languages=languages,
            knockout_hit=qid in ko_ids,
        )
        # Strengthen: if skill is in profile but not on resume → not_evidenced for Lens
        n = q.get("normalized") or {}
        if n.get("type") == "skill" and v["verdict"] == "met":
            name = str(n.get("name") or "").lower()
            if (
                name
                and name not in resume_text
                and not any(name == s or name in s for s in shown_skills)
            ):
                # Check profile has it
                if any(name == s or name in s or s in name for s in profile_skills):
                    v = {
                        "verdict": "not_evidenced",
                        "evidence_quote": None,
                        "note": "In profile but not shown on resume",
                        "gap_option": "surface",
                    }
                else:
                    v = {
                        "verdict": "not_evidenced",
                        "evidence_quote": None,
                        "note": None,
                        "gap_option": "skip_or_add_fact",
                    }

        loc = _evidence_location(content, v.get("evidence_quote"))
        row = {
            "qual_id": qid,
            "kind": kind,
            "text": q.get("text") or "",
            "quote": q.get("quote") or "",
            "verdict": v["verdict"],
            "evidence_quote": v.get("evidence_quote"),
            "evidence_location": loc,
            "note": v.get("note"),
            "gap_option": v.get("gap_option"),
        }
        rows.append(row)
        if kind == "must":
            must_total += 1
            if v["verdict"] in {"met", "partial"}:
                must_met += 1
        elif kind == "preferred":
            pref_total += 1
            if v["verdict"] == "met":
                pref_met += 1

    # Weights: must 0.7, preferred 0.3; knockouts separate
    must_score = (must_met / must_total) if must_total else 0.5
    pref_score = (pref_met / pref_total) if pref_total else 0.5
    overall = 0.7 * must_score + 0.3 * pref_score
    if knockouts:
        overall = min(overall, 0.35)

    authenticity = _authenticity(content, facts, linkedin_text=linkedin_text)
    skim = _skim_analysis(content, qualifications)

    notes: list[str] = []
    if long_wishlist:
        notes.append("Long wish list: humans rarely expect every item")
    notes.append("Simulation of ATS/recruiter AI with stated limits; not a guarantee")

    return {
        "grade": _grade(overall),
        "score": round(overall, 3),
        "qualifications": rows,
        "knockouts": knockouts,
        "knockout_pass": len(knockouts) == 0,
        "skim": skim,
        "authenticity": authenticity,
        "parsed": parsed,
        "notes": notes,
        "counts": {
            "must_total": must_total,
            "must_met": must_met,
            "preferred_total": pref_total,
            "preferred_met": pref_met,
        },
    }


def _evidence_location(content: ResumeContent, quote: str | None) -> dict[str, Any] | None:
    if not quote:
        return None
    q = quote.lower()
    for sec in content.sections:
        if sec.kind == "experience":
            for item in sec.items:
                for line in item.lines:
                    if q in line.text.lower() or line.text.lower() in q:
                        return {
                            "role": item.title,
                            "company": item.subtitle,
                            "dates": f"{item.start or ''}-{item.end or ('Present' if item.is_current else '')}",
                            "line_id": line.id,
                        }
        if sec.kind == "skills":
            for line in sec.lines:
                if q in line.text.lower() or line.text.lower() in q:
                    return {"section": "skills", "line_id": line.id}
    if content.summary and q in content.summary.text.lower():
        return {"section": "summary", "line_id": content.summary.id}
    return {"section": "resume"}


def _authenticity(
    content: ResumeContent, facts: dict[str, Any], *, linkedin_text: str | None
) -> dict[str, Any]:
    blob = content.plain_text().lower()
    hits = [p for p in (*_BANNED, *DEFAULT_BANNED_PHRASES) if p in blob]
    inconsistencies: list[str] = []
    profile_companies = {
        str(e.get("company") or "").lower()
        for e in (facts.get("experiences") or [])
        if isinstance(e, dict)
    }
    for sec in content.sections:
        if sec.kind != "experience":
            continue
        for item in sec.items:
            company = (item.subtitle or "").lower()
            if company and profile_companies and company not in profile_companies:
                inconsistencies.append(f"Employer '{item.subtitle}' not in profile")
    if linkedin_text:
        # Soft check: titles present in LinkedIn paste
        for sec in content.sections:
            if sec.kind != "experience":
                continue
            for item in sec.items:
                if item.title and item.title.lower() not in linkedin_text.lower():
                    inconsistencies.append(f"Title '{item.title}' not found in LinkedIn paste")
    return {
        "banned_hits": hits[:10],
        "inconsistencies": inconsistencies[:10],
        "ok": not hits and not inconsistencies,
    }


def _skim_analysis(content: ResumeContent, qualifications: list[dict[str, Any]]) -> dict[str, Any]:
    must_skills = []
    for q in qualifications:
        if q.get("kind") != "must":
            continue
        n = q.get("normalized") or {}
        if n.get("type") == "skill" and n.get("name"):
            must_skills.append(str(n["name"]))
        elif n.get("name"):
            must_skills.append(str(n["name"]))
    top = must_skills[:5]
    zone_parts = []
    if content.summary:
        zone_parts.append(content.summary.text)
    for sec in content.sections:
        if sec.kind == "experience" and sec.items:
            it = sec.items[0]
            zone_parts.append(f"{it.title}, {it.subtitle}")
            zone_parts.extend(line.text for line in it.lines[:3])
            break
    zone = "\n".join(zone_parts)
    visible = [s for s in top if s.lower() in zone.lower()]
    return {
        "zone_text": zone[:600],
        "top_must_haves": top,
        "visible_in_zone": visible,
        "missing_in_zone": [s for s in top if s not in visible],
    }


GRADE_ORDER = ["D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A"]


def grade_rank(grade: str) -> int:
    try:
        return GRADE_ORDER.index(grade)
    except ValueError:
        return 0


def must_coverage(report: dict[str, Any]) -> float:
    c = report.get("counts") or {}
    total = int(c.get("must_total") or 0)
    if not total:
        return 1.0
    return int(c.get("must_met") or 0) / total
