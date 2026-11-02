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
# Words that are capitalized for grammar, not because they name something.
_SENTENCE_STARTERS = frozenset(
    {
        "i",
        "we",
        "the",
        "a",
        "an",
        "my",
        "our",
        "this",
        "that",
        "led",
        "built",
        "managed",
        "designed",
        "created",
        "developed",
        "delivered",
        "owned",
        "ran",
        "shipped",
        "improved",
        "reduced",
        "increased",
        "partnered",
        "collaborated",
        "mentored",
        "wrote",
        "launched",
        "drove",
        "established",
        "supported",
        "worked",
        "using",
        "with",
    }
)


def _proper_nouns(text: str) -> list[str]:
    """Capitalized names mid-sentence: employers, products, technologies, places.

    The first word is skipped because sentence case capitalizes it regardless of meaning.
    """
    out: list[str] = []
    for i, word in enumerate(text.split()):
        core = word.strip(".,;:()[]\"'!?")
        if i == 0 or len(core) < 2 or not core[0].isupper():
            continue
        if core.lower() in _SENTENCE_STARTERS:
            continue
        if core.isupper() and len(core) <= 1:
            continue
        out.append(core)
    return out


def _profile_skill_names(facts: dict[str, Any]) -> list[str]:
    return [
        str(s.get("name") or "").strip()
        for s in (facts.get("skills") or [])
        if isinstance(s, dict) and str(s.get("name") or "").strip()
    ]


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


def verify_line(
    line: ResumeLine,
    facts: dict[str, Any],
    *,
    allowed_entities: set[str] | None = None,
) -> list[dict[str, Any]]:
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

    # Skills named on the line must be evidenced by this line's own refs, not just the profile.
    evid_low = evidence.lower()
    for skill in _profile_skill_names(facts):
        if skill.lower() in low and skill.lower() not in evid_low:
            rejected.append(
                {
                    "line_id": line.id,
                    "reason": "unsupported_skill",
                    "detail": f"Skill {skill} is not in this line's evidence",
                }
            )

    # Named entities (employers, products, technologies) must come from the evidence too.
    # `allowed_entities` carries names from the target job (company, title) that are not profile
    # facts but are legitimate to mention.
    allowed = allowed_entities or set()
    for noun in _proper_nouns(line.text):
        low_noun = noun.lower()
        if low_noun in evid_low or low_noun in profile or low_noun in allowed:
            continue
        rejected.append(
            {
                "line_id": line.id,
                "reason": "unsupported_entity",
                "detail": f"Named entity {noun} has no profile evidence",
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
    allowed_entities: set[str] | None = None,
) -> VerifyResult:
    line = ResumeLine(text=after_text, evidence_refs=evidence_refs)
    rejected = verify_line(line, facts, allowed_entities=allowed_entities)
    return VerifyResult(ok=not rejected, rejected=rejected, gaps=[r["detail"] for r in rejected])
