"""Answer Desk evals: AI-restriction recall + fabrication/banned lint (lite)."""

from __future__ import annotations

import json
from pathlib import Path

from app.answers.draft import draft_answer
from app.answers.restriction import detect_ai_restriction
from app.answers.split import split_questions
from app.profiles.banned_phrases import DEFAULT_BANNED_PHRASES

FIX = Path(__file__).parent / "fixtures" / "answer_desk" / "restriction_corpus.jsonl"


def test_restriction_corpus_recall():
    rows = [json.loads(line) for line in FIX.read_text().splitlines() if line.strip()]
    positives = [r for r in rows if r["label"] == "restricted"]
    negatives = [r for r in rows if r["label"] == "clear"]
    assert len(positives) >= 80
    langs = {r.get("lang") for r in positives}
    assert len(langs) >= 2  # corpus mixes languages

    hits = sum(1 for r in positives if detect_ai_restriction(r["text"]).restricted)
    recall = hits / len(positives)
    assert recall >= 0.98, f"restriction recall {recall:.3f} ({hits}/{len(positives)})"

    fps = sum(1 for r in negatives if detect_ai_restriction(r["text"]).restricted)
    assert fps == 0, f"false positives: {fps}"


def test_splitter_char_limits():
    qs = split_questions(
        "1. First? (max 100 characters)\n2. Second question with max 500 characters?\n3. Third?"
    )
    assert len(qs) == 3
    assert qs[0].char_limit == 100
    assert qs[1].char_limit == 500


def test_draft_fabrication_and_banned():
    profile = {
        "display_name": "Sam",
        "headline": "Backend engineer",
        "summary": "Built APIs in Python",
        "experiences": [{"title": "Engineer", "company": "Acme"}],
        "skills": [{"name": "Python"}],
    }
    # 30 synthetic Qs — drafts must stay grounded (company/skill from profile) and ban-free
    questions = [f"Question {i}: Why are you a good fit for this role?" for i in range(30)]
    banned_lower = {p.lower() for p in DEFAULT_BANNED_PHRASES}
    for q in questions:
        out = draft_answer(question=q, profile=profile)
        assert out["source"] in {"draft", "needs_story"}
        text = (out["draft"] or "").lower()
        assert "acme" in text or "python" in text or "sam" in text
        for phrase in banned_lower:
            assert phrase not in text, phrase
        assert out["evidence_refs"]
