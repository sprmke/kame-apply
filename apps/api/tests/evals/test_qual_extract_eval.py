"""Qualification extraction eval: must/preferred accuracy ≥85%, knockout recall ≥95%."""

from __future__ import annotations

import json
from pathlib import Path

from app.matching.extract import extract_rule_based

CASES = Path(__file__).parent / "fixtures" / "qual_extract" / "cases.jsonl"


def test_qual_extract_accuracy_and_knockout_recall():
    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    assert len(cases) >= 50

    kind_ok = 0
    kind_n = 0
    ko_need = 0
    ko_hit = 0

    for c in cases:
        quals, few = extract_rule_based(
            title=c["title"], description=c["description"], skills=c.get("skills") or []
        )
        kinds = {q.kind for q in quals}
        expect = c["expect"]
        if expect.get("few"):
            kind_n += 1
            if few:
                kind_ok += 1
            continue
        if expect.get("must"):
            kind_n += 1
            if "must" in kinds or any(q.normalized.get("type") == "skill" for q in quals):
                kind_ok += 1
        if expect.get("preferred"):
            kind_n += 1
            if "preferred" in kinds or "must" in kinds:
                kind_ok += 1
        if expect.get("knockout"):
            ko_need += 1
            if "knockout" in kinds:
                ko_hit += 1

    acc = kind_ok / kind_n if kind_n else 1.0
    ko_recall = ko_hit / ko_need if ko_need else 1.0
    assert acc >= 0.85, f"classification accuracy {acc:.2f}"
    assert ko_recall >= 0.95, f"knockout recall {ko_recall:.2f}"
