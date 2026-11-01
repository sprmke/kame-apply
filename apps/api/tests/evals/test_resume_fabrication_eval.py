"""Phase 8 eval: fabrication rate = 0; parse gate 100% on golden synthetic resumes."""

from __future__ import annotations

import json
from pathlib import Path

from app.resumes.from_profile import build_from_profile
from app.resumes.parse_gate import run_parse_gate
from app.resumes.render import render_all
from app.resumes.verify import verify_content

FIXTURE = Path(__file__).parent / "fixtures" / "resumes" / "profiles.jsonl"


def _load_profiles() -> list[dict]:
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]
    assert len(rows) >= 5
    return rows


def test_fabrication_rate_zero_on_golden_profiles():
    for row in _load_profiles():
        content = build_from_profile(row["profile"], target_role=row.get("target_role"))
        vr = verify_content(content, row["profile"])
        assert vr.ok, (row.get("id"), vr.rejected)
        # Poisoned claim must fail
        poisoned = content.model_copy(deep=True)
        if poisoned.summary:
            poisoned.summary.text = "Grew ARR 999% with zero evidence"
            poisoned.summary.evidence_refs = [str(row["profile"]["id"])]
            assert not verify_content(poisoned, row["profile"]).ok


def test_parse_gate_one_hundred_percent_on_golden():
    fails = []
    for row in _load_profiles():
        content = build_from_profile(row["profile"], target_role=row.get("target_role"))
        content.contact.email = content.contact.email or "candidate@example.com"
        rendered = render_all(content)
        gate = run_parse_gate(content, pdf=rendered.pdf, docx=rendered.docx, text=rendered.text)
        if not gate["ok"]:
            fails.append((row.get("id"), gate["diagnostics"]))
    assert not fails, fails
