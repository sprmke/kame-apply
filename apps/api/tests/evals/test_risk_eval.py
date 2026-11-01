"""Risk eval: false-red on legit ATS < 3%; red recall on scam ≥ 85% (≥100 labeled)."""

from __future__ import annotations

import json
from pathlib import Path

from app.safety.assess import assess_job_text

FIXTURE = Path(__file__).parent / "fixtures" / "risk" / "labeled.jsonl"


def test_risk_calibration_targets():
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]
    assert len(rows) >= 100

    legit = [r for r in rows if r["label"] == "legit"]
    scam = [r for r in rows if r["label"] == "scam"]
    assert len(legit) >= 40
    assert len(scam) >= 40

    false_red = 0
    for r in legit:
        a = assess_job_text(
            title=r["title"],
            description_text=r["text"],
            apply_url=r.get("apply_url") or "https://boards.greenhouse.io/acme/jobs/1",
            source_kind=r.get("source_kind") or "ats",
            company_verified=bool(r.get("verified", True)),
            salary=r.get("salary") or {},
            run_network=False,
            run_llm=False,
        )
        if a.level == "red":
            false_red += 1

    red_hit = 0
    for r in scam:
        a = assess_job_text(
            title=r["title"],
            description_text=r["text"],
            apply_url=r.get("apply_url") or "https://example.com/apply",
            source_kind=r.get("source_kind"),
            company_verified=False,
            run_network=False,
            run_llm=False,
        )
        if a.level == "red":
            red_hit += 1

    false_red_rate = false_red / len(legit)
    red_recall = red_hit / len(scam)
    assert false_red_rate < 0.03, f"false-red {false_red_rate:.2%} on legit ATS"
    assert red_recall >= 0.85, f"red recall {red_recall:.2%} on scam set"
