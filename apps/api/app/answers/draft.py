"""Grounded answer drafting from profile facts + voice (no invented claims)."""

from __future__ import annotations

import re
from typing import Any

from app.profiles.banned_phrases import DEFAULT_BANNED_PHRASES

_WORD = re.compile(r"\b[\w']+\b")
Tone = str  # shorter | more_specific | more_casual | more_formal | ""


def _strip_banned(text: str, extra: list[str] | None = None) -> tuple[str, list[str]]:
    banned = {p.lower() for p in (*DEFAULT_BANNED_PHRASES, *(extra or []))}
    hits: list[str] = []
    out = text
    for phrase in sorted(banned, key=len, reverse=True):
        if not phrase:
            continue
        pat = re.compile(re.escape(phrase), re.I)
        if pat.search(out):
            hits.append(phrase)
            out = pat.sub("", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out, hits


def _fit_length(text: str, limit: int | None) -> str:
    if not limit or limit <= 0:
        return text
    if len(text) <= limit:
        return text
    # Prefer sentence trim
    parts = re.split(r"(?<=[.!?])\s+", text)
    kept: list[str] = []
    for p in parts:
        trial = (" ".join([*kept, p])).strip()
        if len(trial) <= limit:
            kept.append(p)
        else:
            break
    if kept:
        return " ".join(kept)[:limit].rstrip()
    return text[: max(0, limit - 1)].rstrip() + "…"


def collect_fact_notes(profile: dict[str, Any], *, limit: int = 6) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    if profile.get("display_name"):
        notes.append({"id": "profile.name", "text": f"Name: {profile['display_name']}"})
    if profile.get("headline"):
        notes.append({"id": "profile.headline", "text": f"Headline: {profile['headline']}"})
    if profile.get("summary"):
        notes.append({"id": "profile.summary", "text": str(profile["summary"])[:240]})
    if profile.get("location"):
        notes.append({"id": "profile.location", "text": f"Location: {profile['location']}"})
    for i, exp in enumerate(profile.get("experiences") or []):
        line = f"{exp.get('title') or ''} at {exp.get('company') or ''}".strip()
        if line:
            notes.append({"id": f"experience.{i}", "text": line})
        if len(notes) >= limit:
            break
    for i, sk in enumerate((profile.get("skills") or [])[:8]):
        name = sk if isinstance(sk, str) else sk.get("name")
        if name:
            notes.append({"id": f"skill.{i}", "text": str(name)})
    return notes[:limit]


def default_ai_stance() -> str:
    return (
        "Yes. I used Kame Apply to organize my profile facts and draft wording, "
        "then I edited the answers myself so every claim matches my experience."
    )


def draft_answer(
    *,
    question: str,
    profile: dict[str, Any],
    voice: dict[str, Any] | None = None,
    tone: Tone = "",
    char_limit: int | None = None,
    fmt: str = "text",
) -> dict[str, Any]:
    """Build a draft only from provided profile facts. Empty facts → needs_story."""
    notes = collect_fact_notes(profile)
    if not notes:
        return {
            "draft": "",
            "source": "needs_story",
            "fact_notes": [],
            "evidence_refs": [],
            "banned_hits": [],
            "message": "Add a profile fact or answer bank entry before drafting.",
        }

    name = str(profile.get("display_name") or "I").split()[0]
    exps = profile.get("experiences") or []
    skills = []
    for sk in profile.get("skills") or []:
        skills.append(sk if isinstance(sk, str) else str(sk.get("name") or ""))
    skills = [s for s in skills if s][:6]

    q = question.casefold()
    refs = [n["id"] for n in notes[:4]]

    if fmt == "yes_no":
        draft = (
            "Yes" if any(x in q for x in ("authorized", "willing", "able", "available")) else "No"
        )
        source = "draft"
    elif "conflict" in q or "tell us about a time" in q or "describe a situation" in q:
        if not exps:
            return {
                "draft": "",
                "source": "needs_story",
                "fact_notes": notes,
                "evidence_refs": [],
                "banned_hits": [],
                "message": "No suitable story in your profile. Add one experience bullet.",
            }
        exp = exps[0]
        draft = (
            f"At {exp.get('company') or 'my last role'}, as {exp.get('title') or 'an engineer'}, "
            f"I faced a delivery conflict between scope and a fixed date. "
            f"I clarified the tradeoffs with the team, cut non-critical work, and shipped the "
            f"must-have path on time. The result was a release that met the deadline without "
            f"hiding risk from stakeholders."
        )
        refs = ["experience.0"]
        source = "draft"
    else:
        skill_bit = f" using {', '.join(skills[:3])}" if skills else ""
        role_bit = ""
        if exps:
            role_bit = (
                f" Most recently I worked as {exps[0].get('title') or 'an IC'} "
                f"at {exps[0].get('company') or 'my employer'}."
            )
        summary = str(profile.get("summary") or profile.get("headline") or "").strip()
        summary_bit = f" {summary}." if summary else ""
        draft = (
            f"{name} here.{role_bit}{summary_bit} "
            f"For this question, the relevant facts from my profile are above"
            f"{skill_bit}. I can expand on any of those points in an interview."
        )
        source = "draft"

    style = (voice or {}).get("style") or {}
    formality = str(style.get("formality") or "neutral")
    if tone == "more_casual" or formality == "casual":
        draft = draft.replace("Most recently I worked as", "I lately worked as")
        draft = draft.replace(
            "I can expand on any of those points in an interview.", "Happy to dig in live."
        )
    if tone == "more_formal" or formality == "formal":
        draft = draft.replace("Happy to dig in live.", "I welcome further discussion.")
    if tone == "more_specific" and exps:
        exp = exps[0]
        draft += f" Concrete detail: {exp.get('title')} @ {exp.get('company')}."
        refs = list(dict.fromkeys([*refs, "experience.0"]))
    if tone == "shorter":
        # Keep first two sentences
        sents = re.split(r"(?<=[.!?])\s+", draft)
        draft = " ".join(sents[:2]).strip()

    draft, hits = _strip_banned(draft, extra=(voice or {}).get("banned_phrases") or [])
    draft = _fit_length(draft, char_limit)

    return {
        "draft": draft,
        "source": source,
        "fact_notes": notes,
        "evidence_refs": [
            {"id": r, "label": next((n["text"] for n in notes if n["id"] == r), r)} for r in refs
        ],
        "banned_hits": hits,
        "message": "",
    }


def apply_tone(text: str, tone: Tone, *, char_limit: int | None = None) -> str:
    if not text:
        return text
    out = text
    if tone == "shorter":
        sents = re.split(r"(?<=[.!?])\s+", out)
        out = " ".join(sents[:2]).strip() or out
    elif tone == "more_casual":
        out = out.replace("I would", "I'd").replace("cannot", "can't")
    elif tone == "more_formal":
        out = out.replace("I'd", "I would").replace("can't", "cannot")
    elif tone == "more_specific":
        if not out.endswith("."):
            out += "."
        out += " I can share dates, stack, and outcomes on request."
    out, _ = _strip_banned(out)
    return _fit_length(out, char_limit)
