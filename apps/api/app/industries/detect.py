"""Deterministic industry detection from a title, resume snippet, or role description."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.industries.packs.general import GENERAL
from app.industries.registry import get_pack, list_packs
from app.jobs.classify import classify_job


@dataclass(slots=True)
class IndustryDetection:
    pack_key: str
    role_family: str | None = None
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)


def detect_industry(text: str) -> IndustryDetection:
    clean = (text or "").strip()
    if not clean:
        return IndustryDetection(pack_key=GENERAL.key, confidence=0.0, reasons=["empty input"])
    classification = classify_job(clean, clean)
    if not classification.industry_hints:
        return IndustryDetection(
            pack_key=GENERAL.key,
            confidence=0.2,
            reasons=["no curated field matched"],
        )
    key = classification.industry_hints[0]
    pack = get_pack(key) or GENERAL
    lowered = clean.lower()
    family = next(
        (
            item.key
            for item in pack.role_families
            if any(title.lower() in lowered for title in item.titles)
        ),
        None,
    )
    reasons = []
    if classification.facets:
        reasons.append("matched " + ", ".join(sorted(classification.facets)))
    if family:
        reasons.append(f"role family: {family}")
    confidence = 0.9 if family else 0.7
    return IndustryDetection(
        pack_key=key,
        role_family=family,
        confidence=confidence,
        reasons=reasons,
    )


def curated_pack_keys() -> list[str]:
    return [pack.key for pack in list_packs() if pack.key != GENERAL.key]


def draft_custom_pack(description: str, *, base_pack: str | None = None) -> dict:
    """Deterministically select building blocks for a field without a curated pack.

    This is the no-AI fallback for industry_pack_draft.v1. It never adds a new field type or
    weakens a safety rule; it only selects existing building blocks.
    """
    import hashlib

    from app.industries.schema import IndustryPack

    detection = detect_industry(description)
    key = base_pack or detection.pack_key or GENERAL.key
    base = get_pack(key) or GENERAL
    slug = hashlib.sha256(description.strip().lower().encode()).hexdigest()[:8]
    custom_key = f"custom_{slug}"
    family = next((item for item in base.role_families if item.key == detection.role_family), None)
    titles = list(family.titles[:5]) if family else []
    if not titles:
        titles = [item.titles[0] for item in base.role_families[:2] if item.titles]
    if not titles:
        titles = [description.strip()[:80]]
    data = {
        "key": custom_key,
        "version": 1,
        "label_key": f"industry.{custom_key}.label",
        "icon": base.icon,
        "detection": base.detection.model_dump(),
        "role_families": [
            {
                "key": "work",
                "label_key": f"industry.{custom_key}.family.work",
                "titles": titles,
            }
        ],
        "ui": base.ui.model_dump(),
        "facets": [],
        "criteria_defaults": base.criteria_defaults.model_dump(),
        "seniority_ladder": [step.model_dump() for step in base.seniority_ladder],
        "credentials": [],
        "answer_keys": {"add": [], "hide": ["github_url"]},
        "sources": base.sources.model_dump(),
        "matching": base.matching.model_dump(),
        "profile": base.profile.model_dump(),
        "resume": base.resume.model_dump(),
        "ai": {"brief": description.strip()[:600], "vocabulary": []},
        "safety": base.safety.model_dump(),
        "features": base.features.model_dump(),
    }
    pack = IndustryPack.model_validate(data)
    return {
        "key": pack.key,
        "base_pack": base.key,
        "role_family": detection.role_family,
        "pack": pack.model_dump(mode="json"),
    }
