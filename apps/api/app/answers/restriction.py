"""AI-restriction detector: multilingual patterns + light scoring.

Employers that forbid AI assistance must pause drafting (research/04 §5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Explicit phrases across EN / ES / FR / DE / PT / ZH (simplified).
_PHRASES: tuple[str, ...] = (
    # English
    "do not use ai",
    "don't use ai",
    "do not use artificial intelligence",
    "without using ai",
    "without using ai tools",
    "please answer without using ai",
    "answer without using ai tools",
    "no ai tools",
    "no ai assistance",
    "no generative ai",
    "ai tools are not permitted",
    "ai is not allowed",
    "chatgpt is not allowed",
    "do not use chatgpt",
    "do not use generative ai",
    "written without ai",
    "must be written by you",
    "write this yourself",
    "human-written only",
    "human only response",
    "unaided by ai",
    "unaided answers only",
    "prohibited from using ai",
    "you may not use ai",
    "you must not use ai",
    "answers must not be ai generated",
    "ai-generated answers are prohibited",
    "no llm",
    "without llm assistance",
    "do not use large language models",
    "no automated drafting",
    "no automated writing tools",
    "please do not use ai tools",
    "kindly answer without ai",
    "respond without ai assistance",
    "this question prohibits ai",
    "ai use is forbidden",
    "ban on ai assistance",
    "exclude ai tools",
    "refrain from using ai",
    "we prohibit ai-generated content",
    # Spanish
    "no utilice ia",
    "no uses ia",
    "sin usar ia",
    "sin utilizar inteligencia artificial",
    "no use inteligencia artificial",
    "prohibido usar ia",
    "no se permite ia",
    "responda sin ia",
    "respuesta sin ia",
    "sin herramientas de ia",
    "no use chatgpt",
    "prohibido chatgpt",
    "no use herramientas de ia",
    "ia no permitida",
    # French
    "ne pas utiliser l'ia",
    "sans utiliser l'ia",
    "sans intelligence artificielle",
    "interdiction d'utiliser l'ia",
    "l'ia n'est pas autorisée",
    "ne pas utiliser chatgpt",
    "répondez sans ia",
    "sans outils d'ia",
    "ia interdite",
    "pas d'assistance ia",
    "contenu généré par ia interdit",
    # German
    "keine ki verwenden",
    "ohne ki",
    "ohne ki-tools",
    "ki ist nicht erlaubt",
    "keine ki-unterstützung",
    "bitte ohne ki antworten",
    "chatgpt ist nicht erlaubt",
    "ki-generierte antworten verboten",
    "keine generative ki",
    "ki-nutzung verboten",
    "antworten ohne ki",
    # Portuguese
    "não use ia",
    "sem usar ia",
    "sem inteligência artificial",
    "ia não é permitida",
    "proibido usar ia",
    "responda sem ia",
    "sem ferramentas de ia",
    "não use chatgpt",
    "proibido chatgpt",
    "conteúdo gerado por ia proibido",
    "sem assistência de ia",
    # Chinese (simplified + common forms)
    "请勿使用ai",
    "不要使用ai",
    "禁止使用ai",
    "不得使用人工智能",
    "请勿使用人工智能",
    "不要使用chatgpt",
    "禁止chatgpt",
    "禁止使用生成式ai",
    "请自行作答",
    "勿借助ai作答",
    "不得借助人工智能",
    "禁止ai辅助",
)

_PAGE_PHRASES: tuple[str, ...] = (
    "this application prohibits ai",
    "ai tools are prohibited throughout",
    "do not use ai anywhere in this application",
    "all answers must be written without ai",
    "esta solicitud prohíbe el uso de ia",
    "cette candidature interdit l'ia",
    "diese bewerbung verbietet ki",
    "esta candidatura proíbe ia",
    "本申请禁止使用ai",
)

_RX_EXTRA = re.compile(
    r"(?i)\b("
    r"no[- ]ai|"
    r"ai[- ]free|"
    r"hand[- ]written(?:\s+only)?|"
    r"must\s+be\s+your\s+own\s+words|"
    r"your\s+own\s+words\s+only"
    r")\b"
)


@dataclass(frozen=True, slots=True)
class RestrictionHit:
    restricted: bool
    page_level: bool
    matched: str
    score: float


def detect_ai_restriction(text: str, *, page_context: str = "") -> RestrictionHit:
    blob = f"{text or ''}\n{page_context or ''}".strip()
    if not blob:
        return RestrictionHit(False, False, "", 0.0)
    lower = blob.casefold()
    # Normalize fancy quotes / dashes lightly (unicode escapes keep ruff quiet)
    lower = (
        lower.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )

    for p in _PAGE_PHRASES:
        if p in lower:
            return RestrictionHit(True, True, p, 1.0)
    for p in _PHRASES:
        if p in lower:
            return RestrictionHit(True, False, p, 0.95)
    m = _RX_EXTRA.search(lower)
    if m:
        return RestrictionHit(True, False, m.group(0), 0.85)
    return RestrictionHit(False, False, "", 0.0)


def is_ai_use_disclosure_question(text: str) -> bool:
    """Questions that ask whether the candidate used AI (answered truthfully)."""
    t = (text or "").casefold()
    cues = (
        "did you use ai",
        "have you used ai",
        "used artificial intelligence",
        "used chatgpt",
        "used generative ai",
        "was this written with ai",
        "ai to prepare",
        "ai to write",
        "assistência de ia",
        "utilizó ia",
        "avez-vous utilisé l'ia",
        "haben sie ki",
        "usou ia",
        "是否使用了ai",
        "是否使用人工智能",
    )
    return any(c in t for c in cues)


# Exposed for evals / corpus generation helpers
KNOWN_PHRASES: tuple[str, ...] = _PHRASES + _PAGE_PHRASES
