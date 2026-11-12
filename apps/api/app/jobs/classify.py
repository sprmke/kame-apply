"""Rule-first job classification: title -> industry hint + coarse occupation + facets.

No LLM here. The optional bulk-tier tiebreak arrives with IND-9. The rules are derived from the
industry packs, so a new pack adds classification coverage without a code branch.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.industries.packs.general import GENERAL
from app.industries.registry import list_packs
from app.industries.schema import IndustryPack

SHIFT_WORDS = {
    "morning": ("morning shift", "morning shifts", "am shift", "breakfast shift"),
    "afternoon": ("afternoon shift", "afternoon shifts", "pm shift"),
    "evening": ("evening shift", "evening shifts", "dinner service", "dinner shift"),
    "night": ("night shift", "night shifts", "overnight", "graveyard shift"),
    "weekend": ("weekend shift", "weekends required", "weekend availability"),
    "split": ("split shift", "split shifts"),
    "rotating": ("rotating shift", "rotating shifts", "shift rotation"),
}

# A tech title can contain words that also appear in hospitality titles (server, host). Require a
# strong kitchen cue before a front-of-house-only word can classify a posting.
_STRONG_KITCHEN = (
    "chef",
    "cook",
    "commis",
    "kitchen",
    "pastry",
    "baker",
    "sous",
    "brigade",
    "mise en place",
    "haccp",
    "servsafe",
    "food handler",
    "garde manger",
)


@dataclass(slots=True)
class JobClassification:
    industry_hints: list[str] = field(default_factory=list)
    occupation_code: str | None = None
    facets: dict[str, list[str]] = field(default_factory=dict)


def _text_has(blob: str, term: str) -> bool:
    return term.lower() in blob


def _pack_score(pack: IndustryPack, title: str, blob: str) -> int:
    score = 0
    for keyword in pack.detection.title_keywords:
        if keyword in title:
            score += 4
        elif keyword in blob:
            score += 1
    for cue in pack.detection.resume_cues:
        if cue in blob:
            score += 1
    return score


def classify_job(title: str, description: str = "") -> JobClassification:
    title_l = (title or "").lower()
    blob = f"{title_l}\n{(description or '').lower()}"
    strong_kitchen = any(word in blob for word in _STRONG_KITCHEN)

    scores: dict[str, int] = {}
    packs: dict[str, IndustryPack] = {}
    for pack in list_packs():
        if pack.key == GENERAL.key:
            continue
        score = _pack_score(pack, title_l, blob)
        if pack.key == "hospitality" and not strong_kitchen:
            # Do not turn "server engineer" or "host platform" into hospitality.
            score = min(score, 2)
        if score:
            scores[pack.key] = score
            packs[pack.key] = pack

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    hints = [key for key, score in ranked if score >= 4][:3]
    if not hints and ranked:
        hints = [ranked[0][0]]

    facets: dict[str, list[str]] = {}
    shift_hits: list[str] = []
    for shift, phrases in SHIFT_WORDS.items():
        if any(phrase in blob for phrase in phrases) or (shift in blob and "shift" in blob):
            shift_hits.append(shift)
    if shift_hits:
        facets["shifts"] = shift_hits
    pay_hits: list[str] = []
    for key, phrases in {
        "accommodation": ("accommodation", "live-in", "housing provided", "staff housing"),
        "meals": ("meals provided", "staff meals", "free meals", "board and lodging"),
        "tips": ("tips", "tip pool", "gratuities"),
        "service_charge": ("service charge", "service-charge"),
        "transport": ("transport provided", "staff transport", "shuttle service"),
    }.items():
        if any(phrase in blob for phrase in phrases):
            pay_hits.append(key)
    if pay_hits:
        facets["pay_includes"] = pay_hits

    for key in hints or list(packs):
        pack = packs.get(key)
        if pack is None:
            continue
        for facet in pack.facets:
            values = facets.setdefault(facet.key, [])
            for option in facet.options:
                names = [option.key.replace("_", " "), *option.synonyms]
                if any(_text_has(blob, name) for name in names) and option.key not in values:
                    values.append(option.key)
            if not values:
                facets.pop(facet.key, None)
        credentials = facets.setdefault("credentials", [])
        for credential in pack.credentials:
            names = [
                credential.key.replace("_", " "),
                *credential.aliases,
            ]
            if any(_text_has(blob, name) for name in names) and credential.key not in credentials:
                credentials.append(credential.key)
        if not credentials:
            facets.pop("credentials", None)

    occupation = None
    if hints:
        detection = packs[hints[0]].detection
        if detection.isco_groups:
            occupation = detection.isco_groups[0]

    return JobClassification(industry_hints=hints, occupation_code=occupation, facets=facets)
