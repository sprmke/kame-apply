"""PII classifier: ≥100 fields; sensitive recall 100% on the labeled sensitive set."""

from __future__ import annotations

import json
from pathlib import Path

from app.safety.pii import classify_field

FIXTURE = Path(__file__).parent / "fixtures" / "pii" / "fields.jsonl"


def test_pii_sensitive_recall_100():
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]
    assert len(rows) >= 100

    sensitive = [r for r in rows if r["expect"] == "sensitive"]
    assert len(sensitive) >= 40

    misses = []
    for r in sensitive:
        got = classify_field(
            label=r.get("label"),
            name=r.get("name"),
            autocomplete=r.get("autocomplete"),
            input_type=r.get("input_type"),
            pattern=r.get("pattern"),
            country=r.get("country"),
        )
        if got.classification != "sensitive":
            misses.append(r)
    assert misses == [], f"sensitive misses: {misses[:5]}"

    # Non-sensitive should not all collapse to sensitive wrongly for clear public labels.
    public = [r for r in rows if r["expect"] == "public"]
    public_ok = 0
    for r in public:
        got = classify_field(label=r.get("label"), name=r.get("name"))
        if got.classification == "public":
            public_ok += 1
    assert public_ok / max(1, len(public)) >= 0.8
