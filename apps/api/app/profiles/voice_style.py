"""Deterministic writing-style metrics from pasted samples (no LLM required).

Produces a plain-language summary plus numeric fields the answer engine can use.
"""

from __future__ import annotations

import re
from typing import Any

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z']+")
_CONTRACTION = re.compile(
    r"\b(?:I'm|I've|I'd|I'll|you're|you've|you'd|you'll|he's|she's|it's|we're|we've|"
    r"we'd|we'll|they're|they've|they'd|they'll|won't|can't|don't|doesn't|didn't|"
    r"isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't|shouldn't|wouldn't|couldn't|"
    r"mustn't|needn't|that's|there's|here's|what's|who's|let's)\b",
    re.I,
)
_FORMAL = re.compile(
    r"\b(?:furthermore|moreover|therefore|consequently|regarding|pursuant|"
    r"hereby|aforementioned|utilize|facilitate|commence|terminate)\b",
    re.I,
)
_CASUAL = re.compile(
    r"\b(?:yeah|yep|gonna|wanna|kinda|sorta|hey|folks|btw|asap|ok|okay|cool)\b",
    re.I,
)


def _sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _words(text: str) -> list[str]:
    return _WORD.findall(text)


def analyze_samples(samples: list[str]) -> dict[str, Any]:
    """Return style JSON. Empty samples → empty style with a short note."""
    texts = [t.strip() for t in samples if t and t.strip()]
    if not texts:
        return {
            "summary": "Add a few writing samples to build a voice profile.",
            "avg_sentence_length": 0.0,
            "formality": 0.5,
            "contraction_rate": 0.0,
            "vocabulary_level": "mixed",
            "openers": [],
            "closers": [],
            "sample_count": 0,
            "word_count": 0,
        }

    all_sents: list[str] = []
    all_words: list[str] = []
    contractions = 0
    formal_hits = 0
    casual_hits = 0
    for t in texts:
        sents = _sentences(t)
        all_sents.extend(sents)
        words = _words(t)
        all_words.extend(words)
        contractions += len(_CONTRACTION.findall(t))
        formal_hits += len(_FORMAL.findall(t))
        casual_hits += len(_CASUAL.findall(t))

    word_count = len(all_words)
    sent_count = max(len(all_sents), 1)
    avg_len = round(word_count / sent_count, 1)
    contraction_rate = round(contractions / max(word_count, 1), 3)

    # Formality: 0 casual → 1 formal. Contractions and casual words pull down.
    formality = 0.55
    formality += min(0.25, formal_hits * 0.05)
    formality -= min(0.35, contraction_rate * 1.2 + casual_hits * 0.04)
    formality = round(max(0.05, min(0.95, formality)), 2)

    avg_word_len = sum(len(w) for w in all_words) / max(word_count, 1)
    unique_ratio = len({w.lower() for w in all_words}) / max(word_count, 1)
    if avg_word_len >= 6.2 and unique_ratio > 0.55:
        vocab = "elevated"
    elif avg_word_len <= 4.4 or unique_ratio < 0.35:
        vocab = "plain"
    else:
        vocab = "mixed"

    openers = [s[:120] for s in all_sents[:3]]
    closers = [s[:120] for s in all_sents[-3:]]

    summary = _plain_summary(avg_len, formality, contraction_rate, vocab)
    return {
        "summary": summary,
        "avg_sentence_length": avg_len,
        "formality": formality,
        "contraction_rate": contraction_rate,
        "vocabulary_level": vocab,
        "openers": openers,
        "closers": closers,
        "sample_count": len(texts),
        "word_count": word_count,
    }


def _plain_summary(avg_len: float, formality: float, contraction_rate: float, vocab: str) -> str:
    if avg_len < 12:
        length = "short sentences"
    elif avg_len > 22:
        length = "longer sentences"
    else:
        length = "medium-length sentences"

    if formality >= 0.7:
        tone = "formal"
    elif formality <= 0.35:
        tone = "casual"
    else:
        tone = "direct"

    bits = [length, tone]
    if contraction_rate >= 0.02:
        bits.append("uses contractions")
    if vocab == "plain":
        bits.append("plain vocabulary")
    elif vocab == "elevated":
        bits.append("more formal vocabulary")
    else:
        bits.append("avoids jargon when possible")
    return ", ".join(bits)
