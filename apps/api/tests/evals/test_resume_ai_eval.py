"""Eval: AI-generated letters and critiques cannot introduce unevidenced claims.

The model output is simulated, so this runs without a key. It asserts the deterministic gate that
every AI draft passes through before a user sees it.
"""

from __future__ import annotations

from typing import Any

from app.resumes.cover_letter_ai import _verify
from app.resumes.verify import verify_operation

FACTS: dict[str, Any] = {
    "id": "p1",
    "display_name": "Ada Lovelace",
    "headline": "Backend Engineer",
    "summary": "Builds APIs",
    "location": "Remote",
    "experiences": [
        {
            "id": "e1",
            "company": "Analytical Engines",
            "title": "Engineer",
            "start_date": "2019-01-01",
            "end_date": None,
            "is_current": True,
        }
    ],
    "bullets": [
        {
            "id": "b1",
            "experience_id": "e1",
            "text": "Built FastAPI services in Python for 12 teams",
            "skills": ["Python", "FastAPI"],
        }
    ],
    "skills": [{"id": "s1", "name": "Python"}, {"id": "s2", "name": "FastAPI"}],
    "education": [],
    "certifications": [],
    "projects": [],
    "links": [],
}

JOB = {"title": "Backend Engineer", "company_name": "Acme"}

# Each case is (sentence, should_pass).
CASES = [
    ("I built FastAPI services in Python for 12 teams.", True),
    ("I built FastAPI services in Python for 47 teams.", False),
    ("I led the Kubernetes migration at Acme.", False),
    ("I worked as a Backend Engineer at Acme.", True),
    ("I increased revenue 40% at Analytical Engines.", False),
]


def test_ai_letter_sentences_are_grounded():
    passed = []
    for sentence, expected in CASES:
        verdict = verify_operation(
            after_text=sentence,
            evidence_refs=["b1", "p1"],
            facts=FACTS,
            allowed_entities={"backend", "engineer", "acme"},
        )
        passed.append(verdict.ok)
        assert verdict.ok is expected, sentence
    assert sum(passed) == 2


def test_letter_verifier_rejects_any_ungrounded_sentence():
    grounded = "\n\n".join(s for s, ok in CASES if ok)
    assert _verify(grounded, facts=FACTS, job=JOB, refs=["b1", "p1"]) is True
    mixed = grounded + "\n\nI also led the Kubernetes migration."
    assert _verify(mixed, facts=FACTS, job=JOB, refs=["b1", "p1"]) is False
