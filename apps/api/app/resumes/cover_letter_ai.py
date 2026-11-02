"""LLM cover letter drafting with a deterministic verifier and fallback.

The model only sees evidence quotes, the target job (delimited untrusted data), and the user's
voice profile. Every sentence is checked against the profile evidence before it is returned, and
any soft AI stop falls back to the deterministic letter.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import PromptedOutput

from app.ai import prompts
from app.ai.optional import StructuredRunner, try_structured
from app.core.config import Settings
from app.core.security import WorkspaceContext
from app.profiles.banned_phrases import DEFAULT_BANNED_PHRASES
from app.resumes.verify import _BANNED, verify_operation
from app.safety.sanitize import for_ai_context

FEATURE = "cover_letter"
TIER = "standard"
MAX_OUT = 900
MIN_WORDS = 150
MAX_WORDS = 250
_WORD = re.compile(r"\b\w+\b")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_GREETING = re.compile(r"^(dear|hi|hello)\b", re.I)


class AiCoverLetter(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


def _clean(text: str, extra_banned: list[str]) -> str:
    out = text.strip()
    banned = {p.lower() for p in (*DEFAULT_BANNED_PHRASES, *_BANNED, *extra_banned) if p}
    for phrase in sorted(banned, key=len, reverse=True):
        out = re.sub(re.escape(phrase), "", out, flags=re.I)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def _sentences(text: str) -> list[str]:
    body = text.strip()
    paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
    if paragraphs and _GREETING.match(paragraphs[0]):
        paragraphs = paragraphs[1:]
    if len(paragraphs) > 1:
        # Drop the signature line (a short final paragraph, usually just the name).
        if len(_WORD.findall(paragraphs[-1])) <= 3:
            paragraphs = paragraphs[:-1]
    return [s for p in paragraphs for s in _SENTENCE.split(p) if s.strip()]


def _prompt(
    *,
    facts: dict[str, Any],
    job: dict[str, Any],
    matches: list[dict[str, Any]],
    voice: dict[str, Any] | None,
) -> str:
    name = str(facts.get("display_name") or "the candidate").split()[0]
    company = str(job.get("company_name") or job.get("company") or "the company")
    title = str(job.get("title") or "the role")
    posting = for_ai_context(str(job.get("description_text") or "")[:2500], kind="job_posting")
    evidence_lines = []
    for m in matches[:4]:
        quote = str(m.get("evidence_quote") or m.get("text") or "").strip()
        ref = m.get("evidence_ref") or ""
        if quote:
            evidence_lines.append(f"- [{ref}] {quote[:400]}")
    samples = [str(s)[:400] for s in ((voice or {}).get("samples") or [])][:3]
    banned = list((voice or {}).get("banned_phrases") or [])
    return (
        f"Candidate first name: {name}\n"
        f"Role: {title}\n"
        f"Company: {company}\n"
        f"Evidence quotes (the only facts you may claim):\n"
        f"{chr(10).join(evidence_lines) or '- none'}\n"
        f"Writing samples (match this voice):\n"
        f"{chr(10).join(samples) or '- none'}\n"
        f"Banned phrases: {', '.join(banned) or 'none'}\n"
        f"{posting.delimited}\n"
        f"Write a {MIN_WORDS}-{MAX_WORDS} word cover letter. Start with 'Dear hiring team,' and "
        f"end with the first name. Use only the evidence quotes for claims about the candidate. "
        f"Mention at most three matches and one specific reason from the posting. No numbers "
        f"unless they appear verbatim in an evidence quote. No stock phrases."
    )


def _verify(
    text: str,
    *,
    facts: dict[str, Any],
    job: dict[str, Any],
    refs: list[str],
) -> bool:
    if not refs:
        return False
    allowed = {
        token.lower()
        for token in re.split(
            r"[^A-Za-z0-9]+", f"{job.get('title') or ''} {job.get('company_name') or ''}"
        )
        if len(token) > 1
    }
    for sentence in _sentences(text):
        verdict = verify_operation(
            after_text=sentence,
            evidence_refs=refs,
            facts=facts,
            allowed_entities=allowed,
        )
        if not verdict.ok:
            return False
    return True


async def draft_cover_letter_ai(
    ctx: WorkspaceContext,
    settings: Settings,
    *,
    facts: dict[str, Any],
    job: dict[str, Any],
    matches: list[dict[str, Any]],
    voice: dict[str, Any] | None = None,
    run_structured: StructuredRunner | None = None,
    model_factory: Any = None,
) -> dict[str, Any] | None:
    """Return a verified AI letter, or None so the caller can use the deterministic draft."""
    result = await try_structured(
        ctx,
        settings,
        tier=TIER,
        feature=FEATURE,
        system=prompts.COVER_LETTER.system,
        prompt=_prompt(facts=facts, job=job, matches=matches, voice=voice),
        output_type=PromptedOutput(AiCoverLetter),
        max_output_tokens=MAX_OUT,
        run_structured=run_structured,
        model_factory=model_factory,
    )
    if result is None:
        return None

    extra_banned = list((voice or {}).get("banned_phrases") or [])
    text = _clean(result.output.text, extra_banned)
    words = len(_WORD.findall(text))
    if words < MIN_WORDS or words > MAX_WORDS:
        return None
    if any(phrase in text.lower() for phrase in (*DEFAULT_BANNED_PHRASES, *_BANNED)):
        return None

    refs = [str(m["evidence_ref"]) for m in matches if m.get("evidence_ref")]
    if facts.get("id"):
        refs.append(str(facts["id"]))
    refs = list(dict.fromkeys(refs))
    if not _verify(text, facts=facts, job=job, refs=refs):
        return None

    return {
        "content": text.strip() + "\n",
        "word_count": words,
        "evidence_refs": [r for r in refs if r != str(facts.get("id"))],
        "company_reason": "",
        "ok": True,
        "source": "ai",
        "provider": result.provider,
        "model": result.model,
    }
