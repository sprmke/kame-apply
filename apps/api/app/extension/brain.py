"""Server-side field brain: classify → map → resolve → fill instructions."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.answers.restriction import detect_ai_restriction
from app.extension.schemas import ExtractedField, FillInstruction
from app.safety.pii import classify_field

_CANONICAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("first_name", re.compile(r"(?i)\b(first\s*name|given\s*name|fname)\b")),
    ("last_name", re.compile(r"(?i)\b(last\s*name|surname|family\s*name|lname)\b")),
    ("full_name", re.compile(r"(?i)\b(full\s*name|your\s*name|legal\s*name)\b")),
    ("email", re.compile(r"(?i)\b(e-?mail)\b")),
    ("phone", re.compile(r"(?i)\b(phone|mobile|telephone|cell)\b")),
    ("city", re.compile(r"(?i)\b(city|town)\b")),
    ("location", re.compile(r"(?i)\b(location|current\s*city)\b")),
    ("linkedin_url", re.compile(r"(?i)\blinkedin\b")),
    ("github_url", re.compile(r"(?i)\bgithub\b")),
    ("portfolio_url", re.compile(r"(?i)\b(portfolio|personal\s*site|website)\b")),
    ("headline", re.compile(r"(?i)\b(headline|current\s*title|job\s*title)\b")),
    ("summary", re.compile(r"(?i)\b(summary|about\s*you|cover\s*letter)\b")),
    ("resume", re.compile(r"(?i)\b(resume|cv|curriculum)\b")),
    (
        "work_authorization",
        re.compile(r"(?i)\b(authorized\s*to\s*work|work\s*auth|legal\s*right\s*to\s*work)\b"),
    ),
    ("sponsorship", re.compile(r"(?i)\b(sponsorship|visa\s*sponsor)\b")),
    ("salary_expectation", re.compile(r"(?i)\b(salary|compensation|expected\s*pay)\b")),
    (
        "notice_period",
        re.compile(r"(?i)\b(notice\s*period|start\s*date|when\s*can\s*you\s*start)\b"),
    ),
    ("relocation", re.compile(r"(?i)\b(relocat)\b")),
    ("eeo_race", re.compile(r"(?i)\b(race|ethnicity)\b")),
    ("eeo_gender", re.compile(r"(?i)\b(gender|sex)\b")),
    ("eeo_veteran", re.compile(r"(?i)\bveteran\b")),
    ("eeo_disability", re.compile(r"(?i)\bdisability\b")),
    ("how_heard", re.compile(r"(?i)\b(how\s*did\s*you\s*hear|source)\b")),
]


def field_blob(field: ExtractedField) -> str:
    return " ".join(
        x
        for x in (field.label, field.name, field.autocomplete, field.surrounding_text, field.type)
        if x
    )


def map_canonical(field: ExtractedField, cached: dict[str, str] | None = None) -> str | None:
    if cached and field.id in cached:
        return cached[field.id]
    blob = field_blob(field)
    ac = (field.autocomplete or "").lower()
    if ac in {"given-name", "fname"}:
        return "first_name"
    if ac in {"family-name", "lname"}:
        return "last_name"
    if ac in {"name"}:
        return "full_name"
    if ac in {"email"}:
        return "email"
    if ac.startswith("tel"):
        return "phone"
    if ac in {"url"} and "linkedin" in blob.lower():
        return "linkedin_url"
    if field.type == "file" and re.search(r"(?i)resume|cv", blob):
        return "resume"
    for key, pat in _CANONICAL_PATTERNS:
        if pat.search(blob):
            return key
    return None


def signature_hash(*, ats: str, fields: list[ExtractedField]) -> str:
    labels = sorted(
        {(f.label or f.name or f.id).strip().lower() for f in fields if (f.label or f.name or f.id)}
    )
    raw = f"{ats}|{'|'.join(labels)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _link_url(links: list[Any], *needles: str) -> str | None:
    for link in links or []:
        if isinstance(link, dict):
            label = str(link.get("label") or link.get("type") or "").lower()
            url = str(link.get("url") or "")
        else:
            label, url = "", str(link)
        if url and any(n in label or n in url.lower() for n in needles):
            return url
    return None


def profile_value_map(
    profile: dict[str, Any], answers: dict[str, str]
) -> dict[str, tuple[str, str]]:
    """canonical_key → (value, source_ref)."""
    out: dict[str, tuple[str, str]] = {}
    name = str(profile.get("display_name") or "").strip()
    if name:
        parts = name.split(None, 1)
        out["full_name"] = (name, "profile.display_name")
        out["first_name"] = (parts[0], "profile.display_name")
        if len(parts) > 1:
            out["last_name"] = (parts[1], "profile.display_name")
    if profile.get("headline"):
        out["headline"] = (str(profile["headline"]), "profile.headline")
    if profile.get("summary"):
        out["summary"] = (str(profile["summary"])[:2000], "profile.summary")
    if profile.get("location"):
        loc = str(profile["location"])
        out["location"] = (loc, "profile.location")
        out["city"] = (loc.split(",")[0].strip(), "profile.location")
    links = list(profile.get("links") or [])
    li = _link_url(links, "linkedin")
    if li:
        out["linkedin_url"] = (li, "profile.links.linkedin")
    gh = _link_url(links, "github")
    if gh:
        out["github_url"] = (gh, "profile.links.github")
    pf = _link_url(links, "portfolio", "website", "personal")
    if pf:
        out["portfolio_url"] = (pf, "profile.links.portfolio")
    # Contact from user record if provided
    if profile.get("email"):
        out["email"] = (str(profile["email"]), "user.email")
    if profile.get("phone"):
        out["phone"] = (str(profile["phone"]), "profile.phone")
    for key, val in answers.items():
        if val:
            out[key] = (val, f"answer_bank.{key}")
    return out


def plan_fields(
    *,
    fields: list[ExtractedField],
    profile: dict[str, Any],
    answers: dict[str, str],
    page_text: str = "",
    cached_map: dict[str, str] | None = None,
    autofill_allowed: bool = True,
) -> tuple[list[FillInstruction], bool, list[str]]:
    page_hit = detect_ai_restriction("", page_context=page_text[:4000])
    page_restricted = bool(page_hit.page_level or (page_hit.restricted and page_hit.page_level))
    if not page_restricted and page_text:
        whole = detect_ai_restriction(page_text[:1500], page_context="")
        page_restricted = bool(whole.page_level)

    values = profile_value_map(profile, answers)
    instructions: list[FillInstruction] = []
    notes: list[str] = []
    if not autofill_allowed:
        notes.append("Autofill is off for this platform until you opt in under Settings.")
        for f in fields:
            instructions.append(
                FillInstruction(
                    field_id=f.id,
                    action="skip",
                    note="platform_policy",
                    pii_class="personal",
                )
            )
        return instructions, page_restricted, notes

    for f in fields:
        clf = classify_field(
            label=f.label,
            name=f.name,
            autocomplete=f.autocomplete,
            input_type=f.type,
        )
        key = map_canonical(f, cached_map)
        field_restricted = detect_ai_restriction(
            f.label or f.surrounding_text or "", page_context=page_text[:500]
        ).restricted

        if clf.classification == "sensitive" or clf.checkpoint:
            instructions.append(
                FillInstruction(
                    field_id=f.id,
                    action="checkpoint",
                    canonical_key=key,
                    pii_class=clf.classification,
                    checkpoint_kind="sensitive_field",
                    note=clf.reason,
                    confidence=0.0,
                    badge="You type",
                )
            )
            continue

        if page_restricted or field_restricted:
            instructions.append(
                FillInstruction(
                    field_id=f.id,
                    action="checkpoint",
                    canonical_key=key,
                    pii_class=clf.classification,
                    checkpoint_kind="ai_restricted",
                    note="Page or field restricts AI drafts",
                    badge="Restricted",
                )
            )
            continue

        if key == "resume":
            instructions.append(
                FillInstruction(
                    field_id=f.id,
                    action="skip",
                    canonical_key=key,
                    pii_class="personal",
                    note="resume_upload",
                    badge="Resume",
                    confidence=0.9,
                )
            )
            continue

        if key and key in values:
            val, src = values[key]
            action = "select" if f.type in {"select", "radio"} or f.options else "fill"
            if f.options and val:
                match = next((o for o in f.options if o.lower() == val.lower()), None)
                if match is None:
                    match = next((o for o in f.options if val.lower() in o.lower()), None)
                if match is None:
                    instructions.append(
                        FillInstruction(
                            field_id=f.id,
                            action="checkpoint",
                            canonical_key=key,
                            source=src,
                            pii_class=clf.classification,
                            checkpoint_kind="unknown_required" if f.required else "answer_approval",
                            note="No matching option",
                            badge="Review",
                        )
                    )
                    continue
                val = match
            instructions.append(
                FillInstruction(
                    field_id=f.id,
                    action=action,
                    value=val,
                    canonical_key=key,
                    source=src,
                    confidence=0.85 if src.startswith("answer_bank") else 0.75,
                    pii_class=clf.classification,
                    badge=src.split(".")[0],
                )
            )
            continue

        # Free-text custom questions: leave for answer insert / checkpoint if required
        if f.required and (f.type in {"textarea", "text"} or not key):
            instructions.append(
                FillInstruction(
                    field_id=f.id,
                    action="checkpoint",
                    canonical_key=key,
                    pii_class=clf.classification,
                    checkpoint_kind="unknown_required",
                    note="No confident value",
                    badge="Needed",
                )
            )
        else:
            instructions.append(
                FillInstruction(
                    field_id=f.id,
                    action="skip",
                    canonical_key=key,
                    pii_class=clf.classification,
                    confidence=0.0,
                )
            )

    return instructions, page_restricted, notes
