"""Optional cover letter: voice-aware, evidence-backed, no stock phrases."""

from __future__ import annotations

import re
from typing import Any

from app.profiles.banned_phrases import DEFAULT_BANNED_PHRASES
from app.resumes.verify import _BANNED

_WORD = re.compile(r"\b\w+\b")


def draft_cover_letter(
    *,
    facts: dict[str, Any],
    job: dict[str, Any],
    matches: list[dict[str, Any]],
    voice: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a 150-250 word draft from real matches + posting company reason."""
    name = str(facts.get("display_name") or "Candidate").split()[0]
    company = str(job.get("company_name") or job.get("company") or "your team")
    title = str(job.get("title") or "this role")
    posting_bits = str(job.get("description_text") or "")[:800]
    company_reason = _company_reason(company, posting_bits, title)

    match_lines: list[str] = []
    refs: list[str] = []
    for m in matches[:3]:
        quote = str(m.get("evidence_quote") or m.get("text") or "").strip()
        if not quote:
            continue
        match_lines.append(quote.rstrip("."))
        if m.get("evidence_ref"):
            refs.append(str(m["evidence_ref"]))

    if not match_lines:
        base = str(facts.get("headline") or facts.get("summary") or "").strip()
        if base:
            match_lines.append(base.rstrip("."))
            refs.append(str(facts.get("id") or ""))

    style = (voice or {}).get("style") or {}
    formality = str(style.get("formality") or "neutral")
    greeting = "Dear hiring team," if formality != "casual" else f"Hi {company} team,"

    evidence = (
        "Here is concrete evidence from my background that maps to the posting: "
        + "; ".join(match_lines[:3])
        + ". "
        if match_lines
        else ""
    )
    body_core = (
        f"I'm writing to apply for the {title} role at {company}. "
        f"{company_reason} "
        f"{evidence}"
        f"I care about doing the work described in the {title} posting carefully and "
        f"honestly, and I can walk through the details of these projects in an interview. "
        f"If helpful, I can also share how I approached similar constraints, tradeoffs, "
        f"and collaboration patterns on recent teams. "
        f"I would welcome a conversation about how this background fits {title} at {company}. "
        f"I am glad to discuss timeline, scope, and day-to-day expectations whenever it is "
        f"convenient for your team. "
        f"Thank you for your time and consideration.\n\n{name}"
    )

    text = f"{greeting}\n\n{body_core}"
    text = _strip_banned(text, extra=(voice or {}).get("banned_phrases") or [])
    words = _WORD.findall(text)
    guard = 0
    while len(words) < 150 and guard < 5:
        guard += 1
        extra = (
            f" My recent work gives me a practical view of the problems named in the "
            f"{title} posting, and I can bring that context without overstating what I "
            f"have done."
        )
        text = text.replace(
            f"Thank you for your time and consideration.\n\n{name}",
            extra + f"\n\nThank you for your time and consideration.\n\n{name}",
        )
        words = _WORD.findall(text)
    if len(words) > 250:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        kept: list[str] = []
        count = 0
        for s in sentences:
            w = len(_WORD.findall(s))
            if count + w > 240 and kept:
                break
            kept.append(s)
            count += w
        if name not in " ".join(kept):
            kept.append(name)
        text = " ".join(kept)
        words = _WORD.findall(text)

    return {
        "content": text.strip() + ("\n" if not text.endswith("\n") else ""),
        "word_count": len(words),
        "evidence_refs": refs,
        "company_reason": company_reason,
        "ok": 120 <= len(words) <= 280,
    }


def _company_reason(company: str, posting: str, title: str) -> str:
    low = posting.lower()
    for needle, phrase in (
        ("open source", f"{company}'s open-source work stands out in the posting"),
        ("customer", "The posting's focus on customers aligns with how I work"),
        ("scale", f"The scale challenges described for {title} match problems I have worked on"),
        ("product", f"The product focus in this {title} posting is a clear fit"),
        ("healthcare", "The healthcare context in the posting is specific and grounded"),
        ("remote", f"The remote setup described for {title} matches how I deliver"),
    ):
        if needle in low:
            return phrase + "."
    return (
        f"The {title} posting at {company} describes problems I have handled in similar settings."
    )


def _strip_banned(text: str, extra: list[str] | None = None) -> str:
    banned = {p.lower() for p in (*_BANNED, *DEFAULT_BANNED_PHRASES, *(extra or []))}
    out = text
    for phrase in sorted(banned, key=len, reverse=True):
        if phrase and phrase in out.lower():
            out = re.sub(re.escape(phrase), "", out, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip()
