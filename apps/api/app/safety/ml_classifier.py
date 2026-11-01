"""L5 EMSCAD-style TF-IDF + logistic regression classifier.

Model artifact is versioned under `artifacts/`. Train with
`apps/api/scripts/train_emscad_classifier.py` (synthetic seed + optional EMSCAD CSV).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

ARTIFACT_DIR = Path(__file__).with_name("artifacts")
MODEL_PATH = ARTIFACT_DIR / "emscad_tfidf_lr.joblib"
META_PATH = ARTIFACT_DIR / "emscad_tfidf_lr.meta.json"
MODEL_VERSION = "emscad_tfidf_lr_v1"


@dataclass(frozen=True)
class MlVerdict:
    probability: float
    score_delta: int
    top_terms: list[str]
    available: bool


@lru_cache(maxsize=1)
def _load_model():
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib

        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def classify_text(text: str) -> MlVerdict:
    model = _load_model()
    if model is None:
        # Heuristic fallback when artifact missing (CI bootstrap).
        return _heuristic(text)

    try:
        pipe = model
        proba = float(pipe.predict_proba([text or ""])[0][1])
        top: list[str] = []
        try:
            vec = pipe.named_steps["tfidf"]
            clf = pipe.named_steps["clf"]
            X = vec.transform([text or ""])
            # Highest absolute weighted features present in this doc.
            feature_names = vec.get_feature_names_out()
            coefs = clf.coef_[0]
            row = X.tocoo()
            scored = []
            for i, v in zip(row.col, row.data, strict=False):
                scored.append((abs(coefs[i] * v), feature_names[i]))
            scored.sort(reverse=True)
            top = [t for _, t in scored[:8]]
        except Exception:
            top = []
        delta = round(proba * 40)  # up to +40
        return MlVerdict(probability=proba, score_delta=delta, top_terms=top, available=True)
    except Exception:
        return _heuristic(text)


def _heuristic(text: str) -> MlVerdict:
    blob = (text or "").lower()
    terms = []
    score = 0.0
    for t in (
        "telegram",
        "whatsapp",
        "training kit",
        "wire transfer",
        "crypto",
        "no interview",
        "urgent hiring",
        "npm install",
    ):
        if t in blob:
            terms.append(t)
            score += 0.12
    score = min(0.95, score)
    return MlVerdict(
        probability=score,
        score_delta=round(score * 40),
        top_terms=terms[:8],
        available=False,
    )


def model_meta() -> dict[str, Any]:
    if META_PATH.exists():
        return json.loads(META_PATH.read_text())
    return {"version": MODEL_VERSION, "trained": False}
