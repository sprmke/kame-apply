"""Combine L1-L7 into calibrated green/yellow/red."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.safety.rules_engine import thresholds

RiskLevel = Literal["green", "yellow", "red"]
MODEL_VERSION = "safety_v1"


@dataclass
class RiskAssessment:
    level: RiskLevel
    score: float
    reasons: list[dict[str, Any]] = field(default_factory=list)
    layers: dict[str, Any] = field(default_factory=dict)
    model_version: str = MODEL_VERSION
    partial: bool = False


def aggregate(
    *,
    content_hits: list[Any],
    source: Any,
    domain: Any,
    links: Any,
    ml: Any,
    community_delta: int = 0,
    community_reasons: list[dict[str, Any]] | None = None,
    llm: dict[str, Any] | None = None,
    missing_salary_only: bool = False,
) -> RiskAssessment:
    thr = thresholds()
    yellow_at = float(thr.get("yellow", 25))
    red_at = float(thr.get("red", 55))
    verified_red = float(thr.get("verified_ats_red", 70))

    score = 0.0
    reasons: list[dict[str, Any]] = []
    layers: dict[str, Any] = {}
    partial = False

    # L1
    l1_w = 0
    for h in content_hits:
        w = int(getattr(h, "weight", 0) or h.get("weight", 0))
        l1_w += w
        reasons.append(
            {
                "signal": getattr(h, "signal", None) or h.get("signal"),
                "layer": "L1",
                "weight": w,
                "evidence": getattr(h, "evidence", None) or h.get("evidence", ""),
            }
        )
    score += l1_w
    layers["L1"] = {"weight": l1_w, "hits": len(content_hits)}

    # L2
    delta2 = int(getattr(source, "score_delta", 0))
    score += delta2
    layers["L2"] = {
        "label": getattr(source, "label", "unknown"),
        "verified_ats": bool(getattr(source, "verified_ats", False)),
        "delta": delta2,
    }
    if delta2 < 0:
        reasons.append(
            {
                "signal": "source_trust",
                "layer": "L2",
                "weight": delta2,
                "evidence": getattr(source, "evidence", "") or getattr(source, "label", ""),
            }
        )

    # L3
    delta3 = int(getattr(domain, "score_delta", 0))
    score += delta3
    layers["L3"] = {"delta": delta3, "age_days": getattr(domain, "domain_age_days", None)}
    reasons.extend(getattr(domain, "reasons", []) or [])
    partial = partial or bool(getattr(domain, "partial", False))

    # L4
    delta4 = int(getattr(links, "score_delta", 0))
    score += delta4
    layers["L4"] = {"delta": delta4, "final_url": getattr(links, "final_url", None)}
    reasons.extend(getattr(links, "reasons", []) or [])
    partial = partial or bool(getattr(links, "partial", False))

    # L5
    delta5 = int(getattr(ml, "score_delta", 0))
    score += delta5
    layers["L5"] = {
        "probability": getattr(ml, "probability", 0.0),
        "top_terms": getattr(ml, "top_terms", []),
        "available": getattr(ml, "available", False),
        "delta": delta5,
    }
    if delta5 >= 12:
        reasons.append(
            {
                "signal": "ml_classifier",
                "layer": "L5",
                "weight": delta5,
                "evidence": ", ".join(getattr(ml, "top_terms", [])[:5])
                or "elevated scam probability",
            }
        )

    # L7 community (capped; never alone enough for red on verified ATS)
    community_delta = max(-15, min(25, int(community_delta)))
    score += community_delta
    layers["L7"] = {"delta": community_delta}
    if community_reasons:
        reasons.extend(community_reasons)

    # L6 LLM optional
    if llm:
        layers["L6"] = llm
        if llm.get("level") == "red":
            score = max(score, red_at)
            reasons.append(
                {
                    "signal": "llm_judge",
                    "layer": "L6",
                    "weight": 20,
                    "evidence": llm.get("summary") or "LLM elevated risk",
                }
            )
        elif llm.get("level") == "yellow":
            score = max(score, yellow_at)

    # Calibration: missing salary alone never raises risk.
    if missing_salary_only and score < yellow_at and not content_hits:
        score = 0.0

    # Domain age alone caps at yellow.
    only_new_domain = (
        delta3 > 0
        and l1_w == 0
        and delta4 == 0
        and delta5 < 12
        and community_delta <= 0
        and any(r.get("signal") == "new_domain" for r in reasons)
    )

    verified = bool(getattr(source, "verified_ats", False))
    red_threshold = verified_red if verified else red_at

    score = max(0.0, min(100.0, float(score)))

    if only_new_domain:
        level: RiskLevel = "yellow" if score >= yellow_at else "green"
    elif score >= red_threshold:
        level = "red"
    elif score >= yellow_at:
        level = "yellow"
    else:
        level = "green"

    # Verified ATS: community reports alone cannot force red.
    if verified and level == "red" and l1_w < 30 and delta4 < 40 and community_delta > 0:
        if l1_w + delta4 + delta5 < red_threshold:
            level = "yellow"

    return RiskAssessment(
        level=level,
        score=score,
        reasons=reasons,
        layers=layers,
        model_version=MODEL_VERSION,
        partial=partial,
    )


def uncertain_band(assessment: RiskAssessment) -> bool:
    """True when L6 LLM judge should run (mixed signals)."""
    return 20 <= assessment.score < 55 and assessment.level in {"yellow", "green"}
