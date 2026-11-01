"""Bounded logistic-style weight updates from skip / shortlist feedback."""

from __future__ import annotations

from app.matching.rule_score import DEFAULT_WEIGHTS, clamp_weights

# Skip reason → component to down-weight
_SKIP_MAP: dict[str, str] = {
    "too_junior": "seniority",
    "too_senior": "seniority",
    "wrong_title": "title",
    "missing_skills": "skills",
    "salary": "salary",
    "location": "location",
    "too_junior_role": "seniority",
    "company": "location",
}

_LR = 0.04
_MAX_STEP = 0.06


def update_weights(
    current: dict[str, float] | None,
    *,
    action: str,
    skip_reason: str | None = None,
    components: dict[str, float] | None = None,
) -> dict[str, float]:
    """Adjust ranking weights. Never zeroes a component; reorders only."""
    w = clamp_weights(current or DEFAULT_WEIGHTS)
    comps = components or {}
    if action == "shortlist":
        # Boost components that were already high for this job
        for k, v in comps.items():
            if k not in w:
                continue
            if v >= 70:
                w[k] = w[k] + min(_MAX_STEP, _LR * (v / 100.0))
    elif action == "skip":
        key = _SKIP_MAP.get((skip_reason or "").strip().lower().replace(" ", "_"))
        if key and key in w:
            w[key] = w[key] - min(_MAX_STEP, _LR * 1.5)
        elif comps:
            # Soft-penalize the strongest component that still passed (noisy signal)
            top = max(comps, key=lambda x: comps[x])
            if top in w:
                w[top] = w[top] - min(_MAX_STEP, _LR)
    return clamp_weights(w)


def skip_reason_bucket(reason: str | None) -> str:
    r = (reason or "").strip().lower()
    for k in _SKIP_MAP:
        if k.replace("_", " ") in r or k in r.replace(" ", "_"):
            return k
    if "junior" in r:
        return "too_junior"
    if "senior" in r or "overqualified" in r:
        return "too_senior"
    if "salary" in r or "pay" in r or "comp" in r:
        return "salary"
    if "location" in r or "remote" in r or "visa" in r:
        return "location"
    if "skill" in r:
        return "missing_skills"
    if "title" in r or "role" in r:
        return "wrong_title"
    return "other"
