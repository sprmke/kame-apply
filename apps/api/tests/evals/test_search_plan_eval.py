"""Search-plan eval: the deterministic fallback must stay safe on every criteria fixture.

The AI path is exercised by the endpoint tests with an injected runner. This eval guards the
offline path: a usable role signal, real filters, and no invented salary, visa, or location.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.tracks.plan import _baseline, _extract_title

FIXTURES = Path(__file__).parent / "fixtures" / "criteria"


def _all() -> list[Path]:
    return sorted(FIXTURES.glob("*.json"))


@pytest.mark.parametrize("path", _all(), ids=lambda p: p.stem)
def test_baseline_is_structural_and_never_invents_personal_facts(path: Path):
    data = json.loads(path.read_text())
    plan = _baseline(data["text"], [])

    assert plan.has_role_signal()
    assert plan.posting_max_age_days == 21
    assert plan.companies.exclude_agencies is True
    # A field of work may set how a rate is read (month or hour); amounts stay empty.
    assert plan.salary is None or (plan.salary.min is None and plan.salary.max is None)
    assert plan.locations == []
    if plan.visa_sponsorship is not None:
        assert re.search(r"\b(visa|sponsor)", data["text"], re.I)
    if plan.relocation is not None:
        assert re.search(r"\brelocat", data["text"], re.I)


def test_baseline_extracts_role_shape():
    plan = _baseline("Software engineer, remote-friendly, full-time, posted this week", [])
    assert _extract_title("Software engineer, remote-friendly") == "Software engineer"
    assert plan.titles[0].title == "Software engineer"
    assert plan.work_modes == ["remote"]
    assert plan.employment_types == ["full_time"]
    assert plan.posting_max_age_days == 7


def test_title_accuracy_on_english_fixtures():
    hits = total = 0
    for path in _all():
        data = json.loads(path.read_text())
        if (data.get("lang") or "en") != "en":
            continue
        title = _extract_title(data["text"]).casefold()
        want = data["expected"]["titles"][0].casefold()
        total += 1
        if want in title or title in want or len(set(want.split()) & set(title.split())) >= 2:
            hits += 1
    assert total >= 30
    assert hits / total >= 0.85
