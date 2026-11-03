"""Per-qualification verdicts vs profile evidence."""

from __future__ import annotations

import re
from typing import Any, Literal

Verdict = Literal["met", "partial", "not_evidenced", "not_met"]

# Same skill, different spelling. Without this, "Java" matches "JavaScript" via substring.
_ALIASES = {
    "postgres": "postgresql",
    "psql": "postgresql",
    "js": "javascript",
    "ts": "typescript",
    "k8s": "kubernetes",
    "golang": "go",
    "ml": "machinelearning",
    "node": "nodejs",
    "node.js": "nodejs",
    "c++": "cplusplus",
    "c#": "csharp",
    ".net": "dotnet",
}


def _skill_tokens(name: str) -> list[str]:
    parts = [p for p in re.split(r"[^a-z0-9+#.]+", name.lower().strip()) if p]
    return [_ALIASES.get(p, p) for p in parts]


def _skill_key(name: str) -> str:
    return " ".join(_skill_tokens(name))


def _same_skill(a: str, b: str) -> bool:
    return bool(a) and _skill_key(a) == _skill_key(b)


def verdict_for_qual(
    qual: dict[str, Any],
    *,
    profile_skills: set[str],
    profile_years: float,
    profile_degrees: set[str],
    profile_languages: set[str],
    knockout_hit: bool = False,
) -> dict[str, Any]:
    if knockout_hit:
        return {
            "verdict": "not_met",
            "evidence_quote": None,
            "note": "Knockout likely failed",
        }
    n = qual.get("normalized") or {}
    typ = n.get("type")
    text = (qual.get("text") or "").lower()
    quote = qual.get("quote") or qual.get("text")

    if typ == "skill" or (not typ and len(text) < 60):
        name = str(n.get("name") or text).lower().strip()
        # Normalized equality only: substring matching made "Java" match "JavaScript".
        if name and any(_same_skill(name, s) for s in profile_skills):
            hit = next(s for s in profile_skills if _same_skill(name, s))
            return {"verdict": "met", "evidence_quote": hit, "note": None}
        # Partial: shared significant tokens (e.g. "machine learning" vs "learning")
        tokens = {t for t in _skill_tokens(name) if len(t) > 2}
        for s in profile_skills:
            st = {t for t in _skill_tokens(s) if len(t) > 2}
            if tokens and tokens & st:
                return {"verdict": "partial", "evidence_quote": s, "note": None}
        return {"verdict": "not_evidenced", "evidence_quote": None, "note": None}

    if typ == "years":
        need = float(n.get("min_years") or 0)
        if profile_years <= 0:
            return {"verdict": "not_evidenced", "evidence_quote": None, "note": None}
        if profile_years + 0.5 >= need:
            return {
                "verdict": "met",
                "evidence_quote": f"{profile_years:.0f} years experience",
                "note": None,
            }
        if profile_years + 2 >= need:
            return {
                "verdict": "partial",
                "evidence_quote": f"{profile_years:.0f} years experience",
                "note": None,
            }
        return {"verdict": "not_met", "evidence_quote": None, "note": None}

    if typ == "degree":
        raw = (n.get("raw") or text).lower()
        if any(d in raw for d in profile_degrees):
            return {"verdict": "met", "evidence_quote": next(iter(profile_degrees)), "note": None}
        if profile_degrees:
            return {
                "verdict": "partial",
                "evidence_quote": next(iter(profile_degrees)),
                "note": None,
            }
        return {"verdict": "not_evidenced", "evidence_quote": None, "note": None}

    if typ == "language":
        name = str(n.get("name") or "").lower()
        if name in profile_languages:
            return {"verdict": "met", "evidence_quote": name, "note": None}
        return {"verdict": "not_evidenced", "evidence_quote": None, "note": None}

    return {"verdict": "not_evidenced", "evidence_quote": quote, "note": "few stated requirements"}
