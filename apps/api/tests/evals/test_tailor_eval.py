"""Phase 9 eval: fabrication 0; Lens grade never decreases unexplained; must coverage."""

from __future__ import annotations

import json
from pathlib import Path

from app.resumes.from_profile import build_from_profile
from app.resumes.lens import grade_rank, must_coverage, run_lens
from app.resumes.tailor import tailor_once
from app.resumes.verify import verify_content

FIXTURE = Path(__file__).parent / "fixtures" / "tailor" / "pairs.jsonl"


def _load():
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]
    assert len(rows) >= 10
    return rows


def test_tailor_fabrication_zero_and_grade_monotonic():
    drops = []
    coverage_miss = []
    for row in _load():
        facts = row["profile"]
        quals = row["qualifications"]
        content = build_from_profile(facts, target_role=row.get("target_role"))
        before = run_lens(content, qualifications=quals, facts=facts)
        out = tailor_once(content, qualifications=quals, facts=facts)
        assert verify_content(out["content"], facts).ok, row.get("id")
        if grade_rank(out["lens_after"]["grade"]) < grade_rank(before["grade"]):
            if not any(
                "decreased" in str(n).lower() or "kept base" in str(n).lower()
                for n in out["review"]
            ):
                drops.append(row.get("id"))
        # Evidence-available musts: skills present in profile
        profile_skills = {
            str(s.get("name") or "").lower()
            for s in (facts.get("skills") or [])
            if isinstance(s, dict)
        }
        evid_musts = [
            q
            for q in quals
            if q.get("kind") == "must"
            and str((q.get("normalized") or {}).get("name") or "").lower() in profile_skills
        ]
        if evid_musts:
            after = out["lens_after"]
            # Coverage among evidenced musts on the tailored resume
            met = 0
            for q in evid_musts:
                qid = str(q.get("id") or "")
                for r in after.get("qualifications") or []:
                    if str(r.get("qual_id")) == qid and r.get("verdict") in {"met", "partial"}:
                        met += 1
                        break
            rate = met / len(evid_musts)
            if rate < 0.95:
                coverage_miss.append((row.get("id"), rate))
    assert not drops, drops
    assert not coverage_miss, coverage_miss


def test_lens_must_coverage_helper_on_pairs():
    for row in _load()[:3]:
        content = build_from_profile(row["profile"], target_role=row.get("target_role"))
        report = run_lens(content, qualifications=row["qualifications"], facts=row["profile"])
        assert 0.0 <= must_coverage(report) <= 1.0
