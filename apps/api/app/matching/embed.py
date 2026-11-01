"""Embeddings for jobs and track/profile vectors (fastembed or hash fallback)."""

from __future__ import annotations

import hashlib
import math
import os
import struct
from collections.abc import Sequence
from functools import lru_cache

DIM = 384
MODEL_BGE = "BAAI/bge-small-en-v1.5"
MODEL_HASH = "hash-v1"


def _hash_vec(text: str, dim: int = DIM) -> list[float]:
    """Deterministic pseudo-embedding for tests / offline CI."""
    v = [0.0] * dim
    tokens = [t for t in text.lower().split() if len(t) > 1] or ["_"]
    for tok in tokens[:256]:
        digest = hashlib.sha256(tok.encode()).digest()
        for i in range(0, min(len(digest), 32), 4):
            idx = struct.unpack_from(">I", digest, i)[0] % dim
            sign = 1.0 if digest[i] % 2 == 0 else -1.0
            v[idx] += sign
    # L2 normalize
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


@lru_cache(maxsize=1)
def _fastembed_model():
    try:
        from fastembed import TextEmbedding
    except ImportError:
        return None
    return TextEmbedding(model_name=MODEL_BGE)


def embed_texts(
    texts: Sequence[str], *, force_hash: bool | None = None
) -> tuple[list[list[float]], str]:
    use_hash = force_hash
    if use_hash is None:
        use_hash = os.environ.get("MATCHING_EMBEDDER", "").lower() in {"hash", "1", "true"}
        if os.environ.get("ENVIRONMENT") == "test" and not os.environ.get("MATCHING_EMBEDDER"):
            use_hash = True
    if use_hash:
        return [_hash_vec(t) for t in texts], MODEL_HASH
    try:
        model = _fastembed_model()
        if model is None:
            return [_hash_vec(t) for t in texts], MODEL_HASH
        out = [list(map(float, vec)) for vec in model.embed(list(texts))]
        return out, MODEL_BGE
    except Exception:
        return [_hash_vec(t) for t in texts], MODEL_HASH


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return max(0.0, min(1.0, dot / (na * nb)))


def job_embed_text(
    *,
    title: str,
    summary: str,
    qualifications: list[str] | None = None,
) -> str:
    parts = [title or "", summary[:1500] if summary else ""]
    if qualifications:
        parts.append(" ".join(qualifications[:30]))
    return "\n".join(p for p in parts if p)


def track_embed_text(*, titles: list[str], skills: list[str], evidence: str = "") -> str:
    return "\n".join(
        [
            " ".join(titles[:10]),
            " ".join(skills[:40]),
            evidence[:1000],
        ]
    )


def similarity_to_score(sim: float) -> float:
    """Map cosine 0-1 → 0-100 with a soft floor."""
    return round(100.0 * (0.15 + 0.85 * sim), 2)
