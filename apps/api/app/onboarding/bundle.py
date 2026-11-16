"""Build the review bundle from one resume reading.

Every claim is quoted back to a line in the sanitized resume text. A value that cannot be found
in the text is dropped by the grounding pass, never shown as a fact (P1). Settings may come from
`suggested` or `default`; a claim about the person may only come from `resume` or `you_said`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.onboarding import schemas as s
from app.onboarding.derive import account as account_rules
from app.onboarding.derive import answers as answer_rules
from app.onboarding.derive import industry as industry_rules
from app.onboarding.derive import prefs
from app.onboarding.derive import seniority as seniority_rules
from app.onboarding.derive import skills as skill_rules
from app.onboarding.derive import studio as studio_rules
from app.onboarding.derive import titles as title_rules
from app.onboarding.derive import voice as voice_rules
from app.onboarding.evidence import evidence
from app.onboarding.parse import country_from_location, parse_resume_text
from app.taxonomy.aliases import skill_key

MAX_SKILLS = 30


@dataclass
class Reading:
    """What the reader understood from one resume, before any review item exists."""

    text: str
    name: str = ""
    headline: str = ""
    summary: str = ""
    location: str = ""
    country: str = ""
    skills: list[str] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    parsed: dict[str, Any] | None = None
    source: str = "rules"

    @property
    def experiences(self) -> list[dict[str, Any]]:
        rows = (self.parsed or {}).get("experiences") or []
        return [row for row in rows if isinstance(row, dict)]


def _confident(value: Any) -> str:
    if isinstance(value, dict):
        raw = value.get("value")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def read_resume(
    text: str,
    *,
    parsed: dict[str, Any] | None = None,
    source: str = "rules",
) -> Reading:
    """Merge the AI draft and the rule parser. Rules fill whatever the model left empty."""
    basics = parse_resume_text(text)
    reading = Reading(text=text, parsed=parsed, source=source)
    if parsed:
        reading.name = _confident(parsed.get("display_name"))
        reading.headline = _confident(parsed.get("headline"))
        reading.summary = _confident(parsed.get("summary"))
        reading.location = _confident(parsed.get("location"))
        reading.skills = [
            str(skill.get("name"))
            for skill in parsed.get("skills") or []
            if isinstance(skill, dict) and skill.get("name")
        ][:MAX_SKILLS]
        reading.links = [
            {"label": str(link.get("label") or "Portfolio")[:80], "url": str(link.get("url"))[:500]}
            for link in parsed.get("links") or []
            if isinstance(link, dict) and str(link.get("url") or "").startswith("https://")
        ][:30]
    reading.name = reading.name or basics["name"]
    reading.headline = reading.headline or basics["headline"]
    reading.location = reading.location or basics["location"]
    reading.skills = reading.skills or list(basics["skills"])[:MAX_SKILLS]
    reading.links = reading.links or list(basics["links"])
    reading.country = country_from_location(reading.location)
    return reading


def _value_item(
    *,
    item_id: str,
    target: str,
    value: Any,
    reading: Reading,
    document_id: uuid.UUID,
    quote: str,
    confidence: float = 0.9,
    reason: str = "setup.reason.resume_line",
) -> s.SetupItem | None:
    refs = evidence(document_id, reading.text, quote)
    if not refs:
        return None
    return s.SetupItem(
        id=item_id,
        group="profile",
        target=target,
        kind="value",
        value=value,
        source="resume",
        confidence=confidence,
        evidence=refs,
        reason_key=reason,
    )


def _entity_item(
    *,
    item_id: str,
    target: str,
    value: dict[str, Any],
    reading: Reading,
    document_id: uuid.UUID,
    quote: str,
    confidence: float = 0.9,
) -> s.SetupItem | None:
    refs = evidence(document_id, reading.text, quote)
    if not refs:
        return None
    return s.SetupItem(
        id=item_id,
        group="profile",
        target=target,
        kind="entity",
        value=value,
        source="resume",
        confidence=confidence,
        evidence=refs,
        reason_key="setup.reason.resume_line",
    )


def _stable_id(prefix: str, value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)[:60]
    return f"{prefix}.{slug or 'item'}"


def _profile_items(reading: Reading, document_id: uuid.UUID) -> list[s.SetupItem]:
    items: list[s.SetupItem] = []
    header = (
        ("profile.display_name", reading.name, reading.name),
        ("profile.headline", reading.headline, reading.headline),
        ("profile.summary", reading.summary, reading.summary),
        ("profile.location", reading.location, reading.location),
    )
    for target, value, quote in header:
        if not value:
            continue
        item = _value_item(
            item_id=target,
            target=target,
            value=value,
            reading=reading,
            document_id=document_id,
            quote=quote,
        )
        if item is not None:
            items.append(item)

    usage = skill_rules.usage(reading.experiences)
    for skill in reading.skills:
        name = str(skill).strip()
        if not name:
            continue
        skill_value: dict[str, Any] = {"name": name, "source": "parsed"}
        data = usage.get(skill_key(name))
        if data and data.get("years"):
            skill_value["years"] = data["years"]
            skill_value["last_used"] = data["last_used"]
        item = _entity_item(
            item_id=f"profile.skill.{_stable_id('s', name)}",
            target="profile.skill",
            value=skill_value,
            reading=reading,
            document_id=document_id,
            quote=name,
            confidence=0.8,
        )
        if item is not None:
            items.append(item)

    for exp in reading.experiences:
        company = str(exp.get("company") or "").strip()
        title = str(exp.get("title") or "").strip()
        if not company or not title:
            continue
        value = {
            key: exp.get(key)
            for key in (
                "company",
                "title",
                "employment_type",
                "location",
                "start_date",
                "end_date",
                "is_current",
                "description",
            )
            if exp.get(key) not in (None, "")
        }
        value["source"] = "parsed"
        item = _entity_item(
            item_id=_stable_id("profile.experience", f"{company}-{title}-{exp.get('start_date')}"),
            target="profile.experience",
            value=value,
            reading=reading,
            document_id=document_id,
            quote=str(exp.get("span") or title),
            confidence=float(exp.get("confidence") or 0.7),
        )
        if item is not None:
            items.append(item)

    for key, target, required in (
        ("projects", "profile.project", "name"),
        ("education", "profile.education", "institution"),
        ("certifications", "profile.certification", "name"),
        ("languages", "profile.spoken_language", "name"),
    ):
        for row in (reading.parsed or {}).get(key) or []:
            if not isinstance(row, dict):
                continue
            label = str(row.get(required) or "").strip()
            if not label:
                continue
            value = {k: v for k, v in row.items() if v not in (None, "")}
            value.pop("bullets", None)
            value["source"] = "parsed"
            item = _entity_item(
                item_id=_stable_id(f"profile.{key}", label),
                target=target,
                value=value,
                reading=reading,
                document_id=document_id,
                quote=str(row.get("span") or label),
                confidence=float(row.get("confidence") or 0.7),
            )
            if item is not None:
                items.append(item)

    return items


def _writing_item(reading: Reading) -> s.SetupItem:
    latest = str(reading.experiences[0].get("title") or "") if reading.experiences else ""
    levels = seniority_rules.suggest_levels(
        latest_title=latest or reading.headline,
        experiences=reading.experiences,
    )
    return s.SetupItem(
        id="writing.preset",
        group="writing",
        target="writing.preset",
        kind="value",
        value=voice_rules.preset_for(headline=reading.headline, levels=levels),
        source="suggested",
        confidence=0.6,
        reason_key="setup.reason.recommended_default",
        default_on=True,
    )


def _studio_item(reading: Reading) -> s.SetupItem:
    return s.SetupItem(
        id="studio.base_resume",
        group="studio",
        target="studio.base_resume",
        kind="value",
        value=studio_rules.base_resume(headline=reading.headline, country=reading.country),
        source="suggested",
        confidence=0.7,
        reason_key="setup.reason.page_size_country"
        if reading.country
        else "setup.reason.recommended_default",
        default_on=True,
    )


def _counts(items: list[s.SetupItem], searches: list[s.SearchProposal]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.group] = counts.get(item.group, 0) + 1
    counts["searches"] = len(searches)
    counts["needs_you"] = sum(1 for item in items if item.needs_you)
    return counts


def build_bundle(
    *,
    reading: Reading,
    document_id: uuid.UUID,
    signals: list[prefs.Signal] | None = None,
    searches: list[s.SearchProposal] | None = None,
    subject: str = "self",
    user: Any = None,
    device_timezone: str = "UTC",
    notices: list[str] | None = None,
    profile_merge: dict[str, Any] | None = None,
) -> s.SetupBundle:
    """One bundle for the review screen. Evidence-less claims never make it in."""
    signal_list = list(signals or [])
    items = _profile_items(reading, document_id)
    items.extend(
        answer_rules.build(
            text=reading.text,
            document_id=document_id,
            links=reading.links,
            signals=signal_list,
            resume_country=reading.country,
        )
    )
    items.append(_writing_item(reading))
    items.append(_studio_item(reading))
    account_items, account_notices = account_rules.account_items(
        subject=subject,
        user=user,
        device_timezone=device_timezone,
        resume_timezone=None,
        resume_name=reading.name,
    )
    items.extend(account_items)
    proposals = list(searches or [])
    notice_keys = list(notices or []) + account_notices
    if reading.source == "rules" and "ai_off_basics_only" not in notice_keys:
        notice_keys.append("ai_off_basics_only")
    hint = industry_rules.detect(reading)
    industry = (
        s.IndustryHint(
            pack_key=hint.pack_key,
            label_key=_pack_label_key(hint.pack_key),
            role_family=hint.role_family,
            confidence=hint.confidence,
        )
        if hint is not None
        else None
    )
    return s.SetupBundle(
        items=items,
        searches=proposals,
        profile_merge=profile_merge,
        notices=notice_keys,
        counts=_counts(items, proposals),
        lowest_pay=_lowest_pay(signal_list),
        industry=industry,
    )


def _pack_label_key(pack_key: str) -> str:
    from app.industries.registry import get_pack

    pack = get_pack(pack_key)
    return pack.label_key if pack is not None else pack_key


def _lowest_pay(signals: list[prefs.Signal]) -> s.SalaryInput | None:
    salary = next(
        (
            signal
            for signal in signals
            if signal.kind == prefs.SignalKind.SALARY and signal.currency
        ),
        None,
    )
    if salary is None:
        return None
    try:
        amount = float(str(salary.value).replace(",", "").replace(" ", ""))
    except ValueError:
        return None
    if amount <= 0:
        return None
    period = salary.period if salary.period in {"hour", "day", "month", "year"} else "month"
    try:
        return s.SalaryInput(
            amount=amount,
            currency=str(salary.currency),
            period=period,  # type: ignore[arg-type]
        )
    except Exception:
        return None


def title_and_synonyms(reading: Reading) -> tuple[list[str], list[str]]:
    """Shared by search building and the review header."""
    return title_rules.role_titles(experiences=reading.experiences, headline=reading.headline)
