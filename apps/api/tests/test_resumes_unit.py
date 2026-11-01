"""Phase 8 unit: content, verify, critique, render, parse gate, generate."""

from __future__ import annotations

from app.resumes.content import ContactBlock, ResumeContent, ResumeLine
from app.resumes.critique import critique_resume
from app.resumes.from_profile import build_from_profile
from app.resumes.generate import apply_accepted_changes, propose_improvements
from app.resumes.parse_gate import run_parse_gate
from app.resumes.render import parse_view, render_all
from app.resumes.verify import verify_content, verify_operation


def _facts(**kw):
    base = {
        "id": "p1",
        "display_name": "Ada Lovelace",
        "headline": "Software Engineer",
        "summary": "Builds analytical engines",
        "location": "London",
        "links": [],
        "experiences": [
            {
                "id": "e1",
                "company": "Analytical Engines",
                "title": "Engineer",
                "start_date": "1840-01-01",
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
                "text": "Wrote algorithms serving 12 clients",
                "metrics": [],
                "skills": ["Mathematics"],
            }
        ],
        "skills": [{"id": "s1", "name": "Mathematics", "level": None, "years": None}],
        "education": [],
        "certifications": [],
    }
    base.update(kw)
    return base


def test_build_from_profile_carries_evidence_refs():
    content = build_from_profile(_facts(), target_role="Software Engineer")
    assert content.summary is not None
    assert "p1" in content.summary.evidence_refs
    assert content.sections[0].items[0].lines[0].evidence_refs == ["b1"]
    assert verify_content(content, _facts()).ok


def test_fabrication_rejected_for_new_numbers():
    line = ResumeLine(text="Grew revenue 400%", evidence_refs=["b1"])
    vr = verify_operation(after_text=line.text, evidence_refs=["b1"], facts=_facts())
    assert not vr.ok
    assert any(r["reason"] == "fabricated_number" for r in vr.rejected)


def test_missing_evidence_rejected():
    content = ResumeContent(
        contact=ContactBlock(full_name="Ada"),
        summary=ResumeLine(text="Invented everything", evidence_refs=[]),
        sections=[],
    )
    vr = verify_content(content, _facts())
    assert not vr.ok


def test_critique_returns_categories_and_top_fixes():
    content = build_from_profile(_facts(), target_role="Software Engineer")
    report = critique_resume(
        content,
        market_skills=[
            {"name": "Python", "frequency": 10},
            {"name": "Mathematics", "frequency": 8},
        ],
        target_role="Software Engineer",
    )
    assert "parseability" in report["categories"]
    assert "market_fit" in report["categories"]
    assert len(report["top_fixes"]) <= 5
    assert "skim_zone" in report


def test_parse_gate_passes_clean_render_fails_broken():
    content = build_from_profile(_facts(), target_role="Software Engineer")
    # Contact email helps parseability but optional for gate when absent
    content.contact.email = "ada@example.com"
    good = render_all(content)
    gate = run_parse_gate(content, pdf=good.pdf, docx=good.docx, text=good.text)
    assert gate["ok"], gate["diagnostics"]
    broken = render_all(content, broken=True)
    bad = run_parse_gate(content, pdf=broken.pdf, docx=broken.docx, text=broken.text)
    assert not bad["ok"]
    assert bad["diagnostics"]


def test_propose_improvements_never_fabricates():
    content = build_from_profile(_facts(), target_role="Software Engineer")
    facts = _facts()
    # Profile has Mathematics; market says show Python (gap) and Mathematics (shown)
    proposals = propose_improvements(
        content,
        critique={"top_fixes": []},
        insights={
            "skills": [
                {"name": "Mathematics", "frequency": 5, "status": "have_shown"},
                {"name": "Python", "frequency": 9, "status": "gap"},
            ],
            "comparison": {"have_not_shown": [], "have_shown": ["Mathematics"], "gap": ["Python"]},
        },
        facts=facts,
    )
    for p in proposals:
        if p.get("after") and p.get("evidence_refs"):
            vr = verify_operation(
                after_text=p["after"],
                evidence_refs=[str(r) for r in p["evidence_refs"]],
                facts=facts,
            )
            assert vr.ok, p


def test_apply_accepted_adds_skill():
    content = build_from_profile(_facts())
    facts = _facts(
        skills=[
            {"id": "s1", "name": "Mathematics", "level": None, "years": None},
            {"id": "s2", "name": "Fortran", "level": None, "years": None},
        ]
    )
    # rebuild skills section with only Mathematics
    updated = apply_accepted_changes(
        content,
        [
            {
                "op": "add_to_skills",
                "after": "Fortran",
                "evidence_refs": ["s2"],
                "status": "accepted",
            }
        ],
    )
    names = [line.text for s in updated.sections if s.kind == "skills" for line in s.lines]
    assert "Fortran" in names
    assert verify_content(updated, facts).ok


def test_parse_view_exposes_ats_fields():
    content = build_from_profile(_facts())
    content.contact.email = "ada@example.com"
    view = parse_view(content)
    assert view["name"] == "Ada Lovelace"
    assert view["email"] == "ada@example.com"
    assert "Experience" in view["sections"] or "experience" in [s.lower() for s in view["sections"]]


def test_golden_fabrication_zero_on_synthetic_set():
    """Scenario 5: every built resume from profile facts verifies clean."""
    roles = [
        ("Backend Engineer", ["Python", "PostgreSQL", "Redis"]),
        ("Data Analyst", ["SQL", "Tableau", "Excel"]),
        ("Nurse", ["Patient care", "Triage", "EMR"]),
    ]
    for i, (role, skills) in enumerate(roles):
        facts = _facts(
            id=f"p{i}",
            headline=role,
            skills=[
                {"id": f"s{i}-{j}", "name": n, "level": None, "years": None}
                for j, n in enumerate(skills)
            ],
            bullets=[
                {
                    "id": f"b{i}",
                    "experience_id": "e1",
                    "project_id": None,
                    "text": f"Delivered {role} work across 3 teams",
                    "metrics": [],
                    "skills": skills[:1],
                }
            ],
        )
        content = build_from_profile(facts, target_role=role)
        vr = verify_content(content, facts)
        assert vr.ok, (role, vr.rejected)
        # Inject fabrication must fail
        content.summary = ResumeLine(text="Increased NPS 99%", evidence_refs=[facts["id"]])
        assert not verify_content(content, facts).ok
