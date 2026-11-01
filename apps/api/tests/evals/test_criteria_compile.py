"""NL criteria compile evals: fixture set ≥60, invent-guard, offline recorded patch accuracy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.tracks.criteria import empty_criteria
from app.tracks.invent_guard import invented_fields
from app.tracks.merge import CriteriaPatch, merge_criteria

FIXTURES = Path(__file__).parent / "fixtures" / "criteria"


def _all() -> list[Path]:
    return sorted(FIXTURES.glob("*.json"))


def test_criteria_fixture_set_size_and_diversity():
    files = _all()
    assert len(files) >= 60
    langs = set()
    for path in files:
        data = json.loads(path.read_text())
        assert data["id"] == path.stem
        assert data["text"].strip()
        assert data["expected"].get("titles")
        langs.add(data.get("lang") or "en")
    assert len(langs) >= 4


@pytest.mark.parametrize("path", _all(), ids=lambda p: p.stem)
def test_recorded_patch_merges_without_inventing_absent_salary(path: Path):
    data = json.loads(path.read_text())
    patch = CriteriaPatch.model_validate(data["recorded_patch"])
    invented = invented_fields(data["text"], patch)
    # Recorded patches are curated; invent-guard should not flag title fields.
    assert "titles" not in invented
    if "salary" in (data["expected"].get("invented_must_not") or []):
        # Ensure a malicious salary patch would be caught
        bad = CriteriaPatch.model_validate(
            {
                **data["recorded_patch"],
                "salary": {"min": 1_000_000, "currency": "USD", "period": "year"},
            }
        )
        assert "salary" in invented_fields(data["text"], bad)
    merged = merge_criteria(empty_criteria(), patch)
    assert merged.has_role_signal()
    want = data["expected"]["titles"][0].casefold()
    got = " ".join(t.title.casefold() for t in merged.titles)
    assert want in got or any(
        want in t.title.casefold() or t.title.casefold() in want for t in merged.titles
    )


def test_field_accuracy_offline_recorded_patches():
    """Title field accuracy ≥ 90% across recorded patches."""
    hits = 0
    total = 0
    for path in _all():
        data = json.loads(path.read_text())
        patch = CriteriaPatch.model_validate(data["recorded_patch"])
        merged = merge_criteria(empty_criteria(), patch)
        total += 1
        want = data["expected"]["titles"][0].casefold()
        titles = [t.title.casefold() for t in merged.titles]
        if any(want in t or t in want for t in titles):
            hits += 1
    assert total >= 60
    assert hits / total >= 0.90
