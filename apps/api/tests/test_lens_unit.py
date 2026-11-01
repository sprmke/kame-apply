"""Phase 9 unit: Recruiter Lens, tailor, stuffing, cover letter."""

from __future__ import annotations

from app.resumes.cover_letter import draft_cover_letter
from app.resumes.from_profile import build_from_profile
from app.resumes.lens import grade_rank, must_coverage, run_lens
from app.resumes.stuffing import enforce_stuffing_caps
from app.resumes.tailor import tailor_once
from app.resumes.verify import verify_content


def _facts():
    return {
        "id": "p1",
        "display_name": "Ada Lovelace",
        "headline": "Backend Engineer",
        "summary": "Builds APIs",
        "location": "Remote",
        "links": [],
        "experiences": [
            {
                "id": "e1",
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2018-01-01",
                "end_date": None,
                "is_current": True,
                "description": None,
            }
        ],
        "projects": [],
        "bullets": [
            {
                "id": "b1",
                "experience_id": "e1",
                "project_id": None,
                "text": "Built FastAPI services for 12 teams",
                "metrics": [],
                "skills": ["Python", "FastAPI"],
            }
        ],
        "skills": [
            {"id": "s1", "name": "Python", "level": None, "years": None},
            {"id": "s2", "name": "FastAPI", "level": None, "years": None},
            {"id": "s3", "name": "PostgreSQL", "level": None, "years": None},
        ],
        "education": [],
        "certifications": [],
    }


def _quals():
    return [
        {
            "id": "q1",
            "kind": "must",
            "text": "Python",
            "quote": "Python",
            "normalized": {"type": "skill", "name": "Python"},
        },
        {
            "id": "q2",
            "kind": "must",
            "text": "PostgreSQL",
            "quote": "PostgreSQL",
            "normalized": {"type": "skill", "name": "PostgreSQL"},
        },
        {
            "id": "q3",
            "kind": "preferred",
            "text": "FastAPI",
            "quote": "FastAPI",
            "normalized": {"type": "skill", "name": "FastAPI"},
        },
    ]


def test_lens_deterministic_and_grades():
    facts = _facts()
    content = build_from_profile(
        {**facts, "skills": facts["skills"][:2]}, target_role="Backend Engineer"
    )
    a = run_lens(content, qualifications=_quals(), facts=facts)
    b = run_lens(content, qualifications=_quals(), facts=facts)
    assert a["grade"] == b["grade"]
    assert a["score"] == b["score"]
    assert a["counts"]["must_met"] == 1


def test_tailor_never_fabricates_and_grade_does_not_drop():
    facts = _facts()
    content = build_from_profile(
        {**facts, "skills": facts["skills"][:2]}, target_role="Backend Engineer"
    )
    before = run_lens(content, qualifications=_quals(), facts=facts)
    out = tailor_once(content, qualifications=_quals(), facts=facts)
    assert verify_content(out["content"], facts).ok
    assert grade_rank(out["lens_after"]["grade"]) >= grade_rank(before["grade"])
    # PostgreSQL was in profile → should surface or remain as gap, never invent years
    blob = out["content"].plain_text().lower()
    assert "99%" not in blob


def test_gap_not_inserted_for_missing_skill():
    facts = _facts()
    facts["skills"] = facts["skills"][:2]  # no PostgreSQL in profile
    content = build_from_profile(facts, target_role="Backend Engineer")
    out = tailor_once(content, qualifications=_quals(), facts=facts)
    assert "postgresql" not in out["content"].plain_text().lower()
    assert (
        any(
            "PostgreSQL" in str(g.get("text") or "") or "postgres" in str(g).lower()
            for g in out["gaps"]
        )
        or out["gaps"]
    )


def test_stuffing_cap_removes_unevidenced_skills():
    facts = _facts()
    content = build_from_profile(facts, target_role="Backend Engineer")
    from app.resumes.content import ResumeLine

    skill_sec = next(s for s in content.sections if s.kind == "skills")
    skill_sec.lines.append(ResumeLine(text="InventedSkill", evidence_refs=[]))
    capped, warnings = enforce_stuffing_caps(content, posting_terms=["Python"])
    names = [line.text for s in capped.sections if s.kind == "skills" for line in s.lines]
    assert "InventedSkill" not in names
    assert warnings


def test_cover_letter_word_band_and_no_banned():
    facts = _facts()
    letter = draft_cover_letter(
        facts=facts,
        job={
            "title": "Backend Engineer",
            "company_name": "Acme",
            "description_text": "We scale product APIs for customers remotely",
        },
        matches=[
            {"evidence_quote": "Built FastAPI services for 12 teams", "evidence_ref": "b1"},
            {"evidence_quote": "Python", "evidence_ref": "s1"},
        ],
    )
    assert letter["ok"]
    assert 120 <= letter["word_count"] <= 280
    low = letter["content"].lower()
    assert "results-driven" not in low
    assert "passionate about" not in low


def test_must_coverage_helper():
    assert must_coverage({"counts": {"must_total": 4, "must_met": 4}}) == 1.0
    assert must_coverage({"counts": {"must_total": 0, "must_met": 0}}) == 1.0
