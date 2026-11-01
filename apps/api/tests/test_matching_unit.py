"""Phase 6 unit tests: extract, filters, score, feedback, relax, embed."""

from __future__ import annotations

from app.matching.embed import cosine, embed_texts, similarity_to_score
from app.matching.extract import extract_rule_based
from app.matching.feedback import skip_reason_bucket, update_weights
from app.matching.hard_filters import hard_filter
from app.matching.knockout import predict_knockouts
from app.matching.relax import suggest_relaxations
from app.matching.rule_score import blend_score, clamp_weights, rule_components
from app.matching.verdicts import verdict_for_qual


def test_extract_must_and_knockout():
    text = """
Requirements:
- 5+ years of Python experience
- Must be based in the US
- Bachelor's degree preferred

Nice to have:
- Kubernetes
"""
    quals, few = extract_rule_based(title="Engineer", description=text, skills=["Python"])
    assert not few
    kinds = {q.kind for q in quals}
    assert "must" in kinds or "knockout" in kinds
    assert any(q.normalized.get("type") == "years" for q in quals) or any(
        "5" in q.text for q in quals
    )
    assert any(q.kind == "knockout" for q in quals)


def test_extract_few_stated():
    quals, few = extract_rule_based(title="X", description="Short", skills=["Go"])
    assert few
    assert quals


def test_hard_filter_title_and_exclude_skill():
    job = {
        "title": "Software Engineer",
        "normalized_title": "software engineer",
        "description_text": "Need Angular experience",
        "work_mode": "remote",
        "skills": [],
        "salary": {},
        "company_name": "Acme",
    }
    crit = {
        "schema_version": 1,
        "titles": [{"title": "Software Engineer", "synonyms": [], "exclude": False}],
        "skills": {"must": [], "nice": [], "exclude": ["Angular"]},
        "work_modes": ["remote"],
    }
    elig, detail = hard_filter(job, crit)
    assert elig == "not_eligible"
    assert any("exclude_skill" in x for x in detail["failed"])


def test_knockout_us_auth():
    hits = predict_knockouts(
        [
            {
                "id": "1",
                "kind": "knockout",
                "quote": "Must be a US citizen",
                "normalized": {"type": "authorization", "raw": "Must be a US citizen"},
            }
        ],
        profile={"work_authorization": {"countries": ["PH"]}, "years_experience": 5},
        answers={},
    )
    assert hits


def test_rule_score_and_blend():
    job = {
        "title": "Senior Python Engineer",
        "normalized_title": "senior python engineer",
        "description_text": "Python FastAPI PostgreSQL remote",
        "skills": ["Python"],
        "seniority": "senior",
        "work_mode": "remote",
        "salary": {"min": 5000},
        "remote_eligibility": {"anywhere": True},
        "posted_at": None,
    }
    crit = {
        "schema_version": 1,
        "titles": [{"title": "Python Engineer", "synonyms": [], "exclude": False}],
        "skills": {"must": ["Python"], "nice": ["FastAPI"], "exclude": []},
        "seniority": ["senior"],
        "work_modes": ["remote"],
        "remote_eligibility": {"anywhere": True, "regions": [], "countries": []},
        "salary": {"min": 4000, "currency": "USD", "period": "month"},
    }
    comps, reasons = rule_components(job, crit, profile_skills=["Python", "FastAPI"])
    assert comps["skills"] >= 80
    assert comps["title"] >= 65
    score = blend_score(comps, semantic=80.0)
    assert 40 <= score <= 100
    assert reasons


def test_feedback_bounds():
    w = update_weights(None, action="skip", skip_reason="too junior", components={"seniority": 90})
    assert 0.02 <= w["seniority"] <= 0.5
    assert abs(sum(w.values()) - 1.0) < 1e-6
    assert skip_reason_bucket("too junior") == "too_junior"


def test_relaxations_gain():
    jobs = [
        {
            "title": "Engineer",
            "normalized_title": "engineer",
            "description_text": "python",
            "work_mode": "on_site",
            "skills": [],
            "salary": {},
            "company_name": "Acme",
        },
        {
            "title": "Engineer",
            "normalized_title": "engineer",
            "description_text": "python",
            "work_mode": "remote",
            "skills": [],
            "salary": {},
            "company_name": "Acme",
        },
    ]
    crit = {
        "schema_version": 1,
        "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
        "work_modes": ["remote"],
    }
    sugg = suggest_relaxations(
        criteria=crit, jobs=jobs, hard_filter_fn=lambda j, c: hard_filter(j, c)
    )
    assert any(s["gained"] >= 1 for s in sugg)


def test_embed_hash_cosine():
    a, model = embed_texts(["python engineer remote"], force_hash=True)
    b, _ = embed_texts(["python engineer remote"], force_hash=True)
    c, _ = embed_texts(["nurse overnight shift"], force_hash=True)
    assert model == "hash-v1"
    assert cosine(a[0], b[0]) > 0.99
    assert cosine(a[0], c[0]) < cosine(a[0], b[0])
    assert similarity_to_score(0.8) > 50


def test_verdict_skill_met():
    v = verdict_for_qual(
        {"kind": "must", "text": "Python", "normalized": {"type": "skill", "name": "Python"}},
        profile_skills={"python", "fastapi"},
        profile_years=5,
        profile_degrees=set(),
        profile_languages=set(),
    )
    assert v["verdict"] == "met"


def test_clamp_weights():
    w = clamp_weights({"title": 10.0, "skills": 0.01})
    assert abs(sum(w.values()) - 1.0) < 1e-6
    assert all(v > 0 for v in w.values())
