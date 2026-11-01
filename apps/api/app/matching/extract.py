"""Qualification extraction: rule-based (always) + optional LLM bulk tier."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Literal

Kind = Literal["must", "preferred", "knockout"]

_YEARS = re.compile(
    r"(\d+)\+?\s*(?:\+|or more\s+)?(?:years?|yrs?)(?:\s+of)?(?:\s+experience)?",
    re.I,
)
_DEGREE = re.compile(
    r"\b(bachelor'?s?|master'?s?|phd|doctorate|bs|ba|ms|mba|bsc|msc)\b",
    re.I,
)
_AUTH = re.compile(
    r"(work(?:ing)?\s+authori[sz]ation|must be (?:a )?(?:us|u\.s\.|uk|eu) "
    r"(?:citizen|based)|visa|sponsorship|right to work)",
    re.I,
)
_LOC_KO = re.compile(
    r"(must be (?:based|located|live)|only (?:candidates|applicants) (?:in|from)|"
    r"eligible (?:to work )?in)",
    re.I,
)
_LICENSE = re.compile(r"\b(license|licence|certification|certified|rn\b|cpa\b|pe\b)\b", re.I)
_LANG = re.compile(r"\b(fluent|native|proficient)\s+in\s+([A-Za-z]+)", re.I)
_MUST_HDR = re.compile(
    r"(?:^|\n)\s*(?:requirements?|must[- ]haves?|you (?:must|have)|qualifications?|"
    r"what you.?ll need|minimum)\s*:?\s*\n",
    re.I,
)
_PREF_HDR = re.compile(
    r"(?:^|\n)\s*(?:nice to have|preferred|bonus|plus)\s*:?\s*\n",
    re.I,
)
_BULLET = re.compile(r"(?:^|\n)\s*[-*•]\s*(.+)")


@dataclass(slots=True)
class ExtractedQual:
    kind: Kind
    text: str
    quote: str
    normalized: dict[str, Any]


def content_hash(title: str, description: str) -> str:
    blob = f"{title}\n{description}".encode()
    return hashlib.sha256(blob).hexdigest()


def extract_rule_based(
    *,
    title: str,
    description: str,
    skills: list[str] | None = None,
) -> tuple[list[ExtractedQual], bool]:
    """Deterministic extraction for CI and as LLM fallback. Returns (quals, few_stated)."""
    text = (description or "").strip()
    quals: list[ExtractedQual] = []
    # Very short blurbs with no list structure: treat as few-stated.
    if not text or (len(text) < 40 and "-" not in text and "*" not in text):
        for sk in skills or []:
            quals.append(
                ExtractedQual(
                    kind="preferred",
                    text=f"Skill: {sk}",
                    quote=sk,
                    normalized={"type": "skill", "name": sk},
                )
            )
        return quals, True

    # Sectioned bullets
    must_body = _section_after(_MUST_HDR, text)
    pref_body = _section_after(_PREF_HDR, text)
    for line in _bullets(must_body or text[:2500]):
        quals.append(_classify_line(line, default="must"))
    if pref_body:
        for line in _bullets(pref_body):
            quals.append(_classify_line(line, default="preferred"))

    # Skills from structured field
    seen = {
        q.normalized.get("name", "").lower() for q in quals if q.normalized.get("type") == "skill"
    }
    for sk in skills or []:
        if sk.lower() in seen:
            continue
        quals.append(
            ExtractedQual(
                kind="must" if must_body else "preferred",
                text=f"Skill: {sk}",
                quote=sk,
                normalized={"type": "skill", "name": sk},
            )
        )

    # Knockouts from whole text (always; section bullets may mis-kind)
    if _AUTH.search(text):
        m = _AUTH.search(text)
        assert m is not None
        quote = text[max(0, m.start()) : m.end() + 60].split("\n")[0][:200]
        quals.append(
            ExtractedQual(
                kind="knockout",
                text="Work authorization",
                quote=quote.strip(),
                normalized={"type": "authorization", "raw": quote.strip()},
            )
        )
    if _LOC_KO.search(text):
        m = _LOC_KO.search(text)
        assert m is not None
        start = max(0, m.start() - 20)
        quote = text[start : m.end() + 80].split("\n")[0][:200]
        quals.append(
            ExtractedQual(
                kind="knockout",
                text="Location eligibility",
                quote=quote.strip(),
                normalized={"type": "location", "raw": quote.strip()},
            )
        )
    for m in _LANG.finditer(text):
        quals.append(
            ExtractedQual(
                kind="knockout",
                text=f"Language: {m.group(2)}",
                quote=m.group(0)[:200],
                normalized={"type": "language", "name": m.group(2)},
            )
        )
        break

    # Deduplicate by (kind, text)
    uniq: dict[tuple[str, str], ExtractedQual] = {}
    for q in quals:
        uniq[(q.kind, q.text.lower()[:120])] = q
    out = list(uniq.values())
    few = len(out) < 3
    return out, few


def _section_after(hdr: re.Pattern[str], text: str) -> str | None:
    m = hdr.search(text)
    if not m:
        return None
    rest = text[m.end() :]
    # Stop at next all-caps-ish header
    stop = re.search(r"\n\s*[A-Z][A-Za-z &/]{2,40}\s*:?\s*\n", rest)
    return rest[: stop.start()] if stop else rest[:2000]


def _bullets(body: str) -> list[str]:
    lines = [m.group(1).strip() for m in _BULLET.finditer(body)]
    if lines:
        return [x for x in lines if len(x) > 2][:40]
    # Fallback: sentences
    parts = re.split(r"[.\n]", body)
    return [p.strip() for p in parts if 12 < len(p.strip()) < 220][:20]


def _classify_line(line: str, *, default: Kind) -> ExtractedQual:
    kind: Kind = default
    normalized: dict[str, Any] = {"type": "other"}
    if _AUTH.search(line) or _LOC_KO.search(line):
        kind = "knockout"
        normalized = {
            "type": "authorization" if _AUTH.search(line) else "location",
            "raw": line[:200],
        }
    elif m := _YEARS.search(line):
        normalized = {"type": "years", "min_years": int(m.group(1))}
    elif _DEGREE.search(line):
        normalized = {"type": "degree", "raw": line[:120]}
    elif _LICENSE.search(line):
        normalized = {"type": "license", "raw": line[:120]}
    elif m := _LANG.search(line):
        normalized = {"type": "language", "name": m.group(2)}
        kind = "knockout"
    else:
        # Treat short noun phrases as skills
        skill = re.sub(r"^(experience with|proficiency in|knowledge of)\s+", "", line, flags=re.I)
        skill = skill.strip(" .")
        if 2 < len(skill) < 60:
            normalized = {"type": "skill", "name": skill}

    if "required" in line.lower() or "must " in line.lower():
        if kind != "knockout":
            kind = "must"
    if "preferred" in line.lower() or "nice to have" in line.lower():
        if kind != "knockout":
            kind = "preferred"

    return ExtractedQual(kind=kind, text=line[:300], quote=line[:200], normalized=normalized)
