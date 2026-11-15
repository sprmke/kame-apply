"""Inline match terms for a posting: what the user has, what is adjacent, what is missing.

Terms come from a curated vocabulary of named skills plus the user's own profile
skill names. Verdicts come from the profile and the stored qualification ledger.
The API returns short labels and surface variants only; posting sentences never
travel back to the client through this path.
"""

from __future__ import annotations

from typing import Any, Literal

from app.taxonomy.aliases import skill_key
from app.taxonomy.skills import (
    SkillHit,
    canonical_skill_label,
    count_surface,
    find_skill_terms,
    skill_blocked_after,
    skill_case_sensitive,
    skill_surfaces,
)
from app.tracks.criteria import CriteriaV1, criteria_from_dict

MatchVerdict = Literal["met", "partial", "gap"]


def _criteria(value: CriteriaV1 | dict[str, Any] | None) -> CriteriaV1:
    if isinstance(value, CriteriaV1):
        return value
    return criteria_from_dict(value)


# Enough to summarize a posting without turning the header into a word cloud.
_CAPS: dict[MatchVerdict, int] = {"met": 10, "partial": 3, "gap": 8}
_ORDER: dict[MatchVerdict, int] = {"met": 0, "partial": 1, "gap": 2}


def _verdict_value(raw: str | None) -> MatchVerdict | None:
    if raw == "met":
        return "met"
    if raw == "partial":
        return "partial"
    if raw in {"not_evidenced", "not_met"}:
        return "gap"
    return None


def build_match_terms(
    *,
    description: str | None,
    profile_skills: list[str],
    criteria: CriteriaV1 | dict[str, Any] | None = None,
    qualifications: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    body = (description or "")[:50_000]
    if not body.strip():
        return []

    resolved = _criteria(criteria)

    hits: dict[str, SkillHit] = {hit.label: hit for hit in find_skill_terms(body)}

    # Profile-only skills (anything outside the curated list) still count when the
    # posting mentions them by name.
    profile_by_key: dict[str, str] = {}
    for raw in profile_skills:
        label = canonical_skill_label(raw)
        if not label:
            continue
        key = skill_key(label)
        profile_by_key.setdefault(key, raw)
        if label in hits:
            continue
        case_sensitive = skill_case_sensitive(label)
        blocked = skill_blocked_after(label)
        for surface in skill_surfaces(label):
            mentions = count_surface(
                body, surface, case_sensitive=case_sensitive, blocked_after=blocked
            )
            if mentions:
                hits[label] = SkillHit(
                    label=label,
                    variants=[surface],
                    mentions=mentions,
                    case_sensitive=case_sensitive,
                )
                break

    qual_verdicts: dict[str, MatchVerdict] = {}
    qual_kinds: dict[str, str] = {}
    for qual in qualifications or []:
        normalized = qual.get("normalized") or {}
        if normalized.get("type") != "skill":
            continue
        name = str(normalized.get("name") or qual.get("text") or "")
        parsed = _verdict_value(qual.get("verdict"))
        if not name or parsed is None:
            continue
        key = skill_key(canonical_skill_label(name))
        # A proven match wins over an unproven one if a posting repeats a skill.
        if qual_verdicts.get(key) != "met":
            qual_verdicts[key] = parsed
        kind = str(qual.get("kind") or "")
        if kind in {"must", "knockout"} or key not in qual_kinds:
            qual_kinds[key] = kind

    excluded = {skill_key(canonical_skill_label(name)) for name in resolved.skills.exclude}
    must = {skill_key(canonical_skill_label(name)) for name in resolved.skills.must}

    rows: list[dict[str, Any]] = []
    for label, hit in hits.items():
        key = skill_key(label)
        if key in excluded:
            continue
        evidence = profile_by_key.get(key)
        if evidence:
            verdict: MatchVerdict = "met"
        else:
            verdict = qual_verdicts.get(key) or "gap"
        patterns = [surface for surface in hit.variants if surface] or [label]
        rows.append(
            {
                "key": key,
                "label": label,
                "patterns": patterns,
                "blocked_after": list(skill_blocked_after(label)),
                "verdict": verdict,
                "mentions": hit.mentions,
                "evidence": evidence if verdict in {"met", "partial"} else None,
                "case_sensitive": hit.case_sensitive,
                "_must": key in must or qual_kinds.get(key) in {"must", "knockout"},
                "_required": hit.required_mentions,
            }
        )

    rows.sort(
        key=lambda row: (
            _ORDER[row["verdict"]],
            0 if row["_must"] else 1,
            -int(row["_required"]),
            -int(row["mentions"]),
            str(row["label"]).casefold(),
        )
    )
    kept: dict[MatchVerdict, int] = {"met": 0, "partial": 0, "gap": 0}
    out: list[dict[str, Any]] = []
    for row in rows:
        verdict = row["verdict"]
        if kept[verdict] >= _CAPS[verdict]:
            continue
        kept[verdict] += 1
        row.pop("_must", None)
        row.pop("_required", None)
        out.append(row)
    return out
