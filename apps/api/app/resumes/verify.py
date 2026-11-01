"""Truthfulness verifier: reject claims without profile evidence (PRD P1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.resumes.content import ResumeContent, ResumeLine

_NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?%?\b")
_BANNED = (
    "results-driven",
    "spearheaded synergies",
    "passionate about leveraging",
    "synergistic",
    "leverage cutting-edge",
    "dynamic self-starter",
)


@dataclass
class VerifyResult:
    ok: bool
    rejected: list[dict[str, Any]] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _profile_header_text(facts: dict[str, Any]) -> str:
    return " ".join(
        str(facts.get(k) or "")
        for k in ("display_name", "headline", "summary", "location", "email", "phone")
    )


def _profile_blob(facts: dict[str, Any]) -> str:
    parts: list[str] = [_profile_header_text(facts)]
    for key in ("experiences", "projects", "bullets", "skills", "education", "certifications"):
        for row in facts.get(key) or []:
            if isinstance(row, dict):
                parts.append(" ".join(str(v) for v in row.values() if v))
            else:
                parts.append(str(row))
    for link in facts.get("links") or []:
        parts.append(str(link))
    return " ".join(parts).lower()


def _evidence_texts(facts: dict[str, Any], refs: list[str]) -> str:
    by_id: dict[str, str] = {}
    if facts.get("id"):
        by_id[str(facts["id"])] = _profile_header_text(facts)
    for key in ("experiences", "projects", "bullets", "skills", "education", "certifications"):
        for row in facts.get(key) or []:
            if isinstance(row, dict) and row.get("id"):
                by_id[str(row["id"])] = " ".join(str(v) for v in row.values() if v)
    return " ".join(by_id.get(r, "") for r in refs).lower()


def verify_line(line: ResumeLine, facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Return rejection records for unsupported numbers/claims on a line."""
    rejected: list[dict[str, Any]] = []
    if line.unverified and not line.evidence_refs:
        rejected.append(
            {
                "line_id": line.id,
                "reason": "unverified_line",
                "detail": "Edited line has no evidence ref",
            }
        )
        return rejected
    if not line.evidence_refs:
        # Skills section lines may list known profile skills without per-line refs
        # if the whole skill name appears in profile skills.
        skill_names = {
            str(s.get("name") or "").lower()
            for s in (facts.get("skills") or [])
            if isinstance(s, dict)
        }
        if line.text.strip().lower() in skill_names:
            return rejected
        rejected.append(
            {
                "line_id": line.id,
                "reason": "missing_evidence",
                "detail": "Claim has no evidence_refs",
            }
        )
        return rejected

    evidence = _evidence_texts(facts, line.evidence_refs)
    profile = _profile_blob(facts)
    for num in _NUMBER.findall(line.text):
        token = num.lower().replace(",", "")
        evid_nums = {n.lower().replace(",", "") for n in _NUMBER.findall(evidence)}
        prof_nums = {n.lower().replace(",", "") for n in _NUMBER.findall(profile)}
        if token not in evid_nums and token not in prof_nums:
            rejected.append(
                {
                    "line_id": line.id,
                    "reason": "fabricated_number",
                    "detail": f"Number {num} not in evidence",
                }
            )
    low = line.text.lower()
    for phrase in _BANNED:
        if phrase in low:
            rejected.append(
                {
                    "line_id": line.id,
                    "reason": "banned_phrase",
                    "detail": phrase,
                }
            )
    return rejected


def verify_content(content: ResumeContent, facts: dict[str, Any]) -> VerifyResult:
    rejected: list[dict[str, Any]] = []
    for line in content.all_lines():
        rejected.extend(verify_line(line, facts))
    gaps = [
        r["detail"] for r in rejected if r["reason"] in {"missing_evidence", "fabricated_number"}
    ]
    return VerifyResult(ok=len(rejected) == 0, rejected=rejected, gaps=gaps)


def verify_operation(
    *,
    after_text: str,
    evidence_refs: list[str],
    facts: dict[str, Any],
) -> VerifyResult:
    line = ResumeLine(text=after_text, evidence_refs=evidence_refs)
    rejected = verify_line(line, facts)
    return VerifyResult(ok=not rejected, rejected=rejected, gaps=[r["detail"] for r in rejected])
