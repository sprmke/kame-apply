"""≥100 normalizer pattern cases (seniority, remote eligibility)."""

from __future__ import annotations

import json
from pathlib import Path

from app.jobs.normalize import infer_seniority, parse_remote_eligibility

CASES = Path(__file__).parent / "evals" / "fixtures" / "normalize_cases.json"


def test_normalize_case_count_and_accuracy():
    cases = json.loads(CASES.read_text())
    assert len(cases) >= 100
    hits = 0
    for c in cases:
        if "expect_seniority" in c:
            if infer_seniority(c["title"]) == c["expect_seniority"]:
                hits += 1
        elif "expect_mode" in c:
            mode, elig = parse_remote_eligibility(
                location=c.get("location") or "",
                remote_flag=c.get("remote"),
                text=c.get("text") or "",
            )
            ok = mode == c["expect_mode"]
            if c.get("expect_countries"):
                ok = ok and elig.get("countries") == c["expect_countries"]
            if ok:
                hits += 1
    assert hits / len(cases) >= 0.95
