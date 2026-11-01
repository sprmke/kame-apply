"""Match a question to the answer bank (variants + embeddings)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.matching.embed import cosine, embed_texts
from app.profiles.answer_keys import CANONICAL_KEYS

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", (s or "").casefold()).strip()


@dataclass(frozen=True, slots=True)
class BankHit:
    answer_id: Any
    key: str
    answer: str
    score: float
    from_bank: bool = True


def match_canonical_key(question: str) -> str | None:
    q = _norm(question)
    best_key: str | None = None
    best = 0.0
    for meta in CANONICAL_KEYS:
        variants = (meta.key.replace("_", " "), meta.label, *meta.default_variants)
        for v in variants:
            nv = _norm(v)
            if not nv:
                continue
            if nv in q or q in nv:
                score = min(1.0, len(nv) / max(len(q), 1))
                if score > best:
                    best, best_key = score, meta.key
            overlap = len(set(nv.split()) & set(q.split()))
            if overlap >= 2:
                score = overlap / max(len(set(nv.split())), 1)
                if score > best:
                    best, best_key = score, meta.key
    return best_key if best >= 0.35 else None


def rank_bank_rows(question: str, rows: list[Any], *, min_score: float = 0.55) -> BankHit | None:
    if not rows:
        return None
    qn = _norm(question)
    # Fast path: variant substring / key
    best: BankHit | None = None
    for row in rows:
        variants = list(row.question_variants or [])
        variants.append(row.key.replace("_", " "))
        for v in variants:
            nv = _norm(v)
            if not nv:
                continue
            if nv in qn or qn in nv:
                score = 0.92
                if best is None or score > best.score:
                    best = BankHit(row.id, row.key, row.answer or "", score)
    if best and best.score >= min_score:
        return best

    # Embedding path
    texts = [question]
    meta: list[tuple[Any, str, str]] = []
    for row in rows:
        variants = list(row.question_variants or []) or [row.key.replace("_", " ")]
        for v in variants[:3]:
            texts.append(v)
            meta.append((row.id, row.key, row.answer or ""))
    vecs, _ = embed_texts(texts, force_hash=True)
    qv = vecs[0]
    for i, (rid, key, ans) in enumerate(meta):
        score = cosine(qv, vecs[i + 1])
        if best is None or score > best.score:
            best = BankHit(rid, key, ans, score)
    if best and best.score >= min_score:
        return best
    return None
