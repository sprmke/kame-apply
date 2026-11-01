# Matching & job board (Phase 6)

Rank Track jobs with explainable scores and triage them on the Jobs board.

## Funnel

1. **Hard filters** (`matching/hard_filters.py`): compiled criteria + knockout predictor + hidden companies → `eligible` / `not_eligible`.
2. **Rule score** (`matching/rule_score.py`): title, must-skills, seniority, salary, freshness (<72h), location/remote.
3. **Semantic** (`matching/embed.py`): fastembed `bge-small-en-v1.5` (or hash embedder in tests via `MATCHING_EMBEDDER=hash`); cosine → 0–100; stored on `jobs.embedding` (pgvector HNSW).
4. **LLM fit** (optional, top N): prompt `job_fit` via bulk tier; skipped when AI unset/budget → `ai_review_paused`.

Final score is a weighted blend; weights live in `tracks.settings.ranking_weights` and shift with skip/shortlist feedback (`matching/feedback.py`, bounded).

## Qualifications

`job_qualifications` (global): kind `must|preferred|knockout`, quote, normalized JSON. Rule extract always runs; cached by `jobs.qualifications_hash`. Knockouts compared to profile + answer bank (`matching/knockout.py`). Per-row verdicts in `track_jobs.fit.ledger`.

## API

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/v1/jobs` | Board list; `track_id`, `sort`, `include_not_eligible` |
| GET | `/api/v1/jobs/export.csv` | Current view CSV |
| GET | `/api/v1/track-jobs/{id}` | Drawer detail |
| POST | `/api/v1/track-jobs/{id}/triage` | shortlist / skip / hide / applied / restore |
| POST | `/api/v1/tracks/{id}/score` | Re-run funnel |
| GET | `/api/v1/tracks/{id}/relaxations` | Zero-result suggestions |
| POST | `/api/v1/hidden-companies` | Hide company |

Discovery `discover_track` calls `score_track_jobs` at the end (LLM top-N disabled inline for latency).

## UI

`/jobs` Reader: list · posting · fit panel. Keyboard `j/k/s/x/o/?`. Track detail shows scored rows + link to board.

## Evals

- Ranking: `tests/evals/test_ranking_eval.py` (≥200 pairs) NDCG@20 / P@10 ≥ rule-only.
- Qual extract: `tests/evals/test_qual_extract_eval.py` (≥50) must/preferred ≥85%, knockout recall ≥95%.
