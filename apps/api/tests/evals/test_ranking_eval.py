"""Ranking eval: NDCG@20 and P@10 must beat rule-only baseline."""

from __future__ import annotations

import json
import math
from pathlib import Path

from app.matching.embed import cosine, embed_texts, similarity_to_score
from app.matching.rule_score import blend_score, rule_components

PAIRS = Path(__file__).parent / "fixtures" / "ranking" / "pairs.jsonl"


def _dcg(rels: list[int], k: int) -> float:
    s = 0.0
    for i, r in enumerate(rels[:k]):
        s += (2**r - 1) / math.log2(i + 2)
    return s


def _ndcg(rels: list[int], k: int) -> float:
    ideal = sorted(rels, reverse=True)
    idcg = _dcg(ideal, k)
    return (_dcg(rels, k) / idcg) if idcg else 0.0


def _precision_at(rels: list[int], k: int) -> float:
    top = rels[:k]
    return sum(top) / len(top) if top else 0.0


def test_ranking_beats_rule_only_baseline():
    rows = [json.loads(line) for line in PAIRS.read_text().splitlines() if line.strip()]
    assert len(rows) >= 200

    # Group by profile
    by_prof: dict[str, list] = {}
    for r in rows:
        by_prof.setdefault(r["profile_id"], []).append(r)

    ndcg_rule = []
    ndcg_full = []
    p10_rule = []
    p10_full = []

    for _pid, items in by_prof.items():
        scored_rule = []
        scored_full = []
        for r in items:
            job = {
                "title": r["title"],
                "normalized_title": r["title"].lower(),
                "description_text": r["desc"],
                "skills": r["skills_must"],
                "seniority": "senior" if "Senior" in r["title"] else "mid",
                "work_mode": "remote" if "remote" in r["desc"].lower() else "on_site",
                "salary": {},
                "remote_eligibility": {"anywhere": "remote" in r["desc"].lower()},
                "posted_at": None,
            }
            crit = {
                "schema_version": 1,
                "titles": [{"title": "Software Engineer", "synonyms": [], "exclude": False}],
                "skills": {"must": ["Python"], "nice": ["FastAPI"], "exclude": []},
                "work_modes": ["remote"],
                "remote_eligibility": {"anywhere": True, "regions": [], "countries": []},
            }
            comps, _ = rule_components(job, crit, profile_skills=r["profile_skills"])
            rule_s = blend_score(comps)
            [jv], _ = embed_texts([f"{r['title']} {r['desc']}"], force_hash=True)
            [pv], _ = embed_texts(
                ["Software Engineer Python FastAPI " + " ".join(r["profile_skills"])],
                force_hash=True,
            )
            sem = similarity_to_score(cosine(jv, pv))
            full_s = blend_score(comps, semantic=sem)
            scored_rule.append((rule_s, r["label"]))
            scored_full.append((full_s, r["label"]))

        scored_rule.sort(key=lambda x: x[0], reverse=True)
        scored_full.sort(key=lambda x: x[0], reverse=True)
        rel_r = [lab for _, lab in scored_rule]
        rel_f = [lab for _, lab in scored_full]
        ndcg_rule.append(_ndcg(rel_r, 20))
        ndcg_full.append(_ndcg(rel_f, 20))
        p10_rule.append(_precision_at(rel_r, 10))
        p10_full.append(_precision_at(rel_f, 10))

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs)

    # Full funnel (rule + semantic) must beat or match rule-only on NDCG@20 and P@10.
    assert mean(ndcg_full) + 1e-9 >= mean(ndcg_rule)
    assert mean(p10_full) + 1e-9 >= mean(p10_rule)
    # Absolute floor: ranking should surface positives
    assert mean(ndcg_full) >= 0.55
    assert mean(p10_full) >= 0.5
