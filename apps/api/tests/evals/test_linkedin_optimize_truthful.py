"""Fabrication guard: optimizer never invents skills not in the profile."""

from __future__ import annotations

import uuid

from app.strategy.linkedin import build_suggestions


def test_optimizer_does_not_invent_track_must_skills():
    out = build_suggestions(
        track_id=uuid.uuid4(),
        track_name="ML",
        structured={
            "titles": [{"title": "ML Engineer", "synonyms": [], "exclude": False}],
            "skills": {"must": ["PyTorch", "CUDA"], "nice": ["Rust"], "exclude": []},
        },
        display_name="Sam",
        headline=None,
        summary="Backend engineer",
        location=None,
        experiences=[{"company": "Acme", "title": "Engineer", "description": "APIs"}],
        skills=["Python", "SQL"],
    )
    joined = " ".join([*out.skills_order, out.headline.text, out.about.text])
    assert "PyTorch" not in joined
    assert "CUDA" not in joined
    assert "Rust" not in joined
    assert out.headline.char_count <= 220
