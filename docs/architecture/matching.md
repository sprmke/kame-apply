# Matching & job board (Phase 6)

Rank Track jobs with explainable scores and triage them on the Jobs board.

## Funnel

1. **Hard filters** (`matching/hard_filters.py`): titles, excluded skills, work mode, employment type, posting age, agencies, knockout predictor, hidden companies → `eligible` / `not_eligible`. Unknown job values (missing employment type or posted date) stay eligible; we do not drop a job for a field the source did not state.
2. **Rule score** (`matching/rule_score.py`): title, must-skills, seniority, salary, freshness (<72h), location/remote.
3. **Semantic** (`matching/embed.py`): fastembed `bge-small-en-v1.5` (or hash embedder in tests via `MATCHING_EMBEDDER=hash`); cosine → 0–100; stored on `jobs.embedding` (pgvector HNSW).
4. **LLM fit** (optional, top N): prompt `job_fit` via bulk tier; skipped when AI unset/budget → `ai_review_paused`.

Final score is a weighted blend; weights live in `tracks.settings.ranking_weights` and shift with skip/shortlist feedback (`matching/feedback.py`, bounded).

## Qualifications

`job_qualifications` (global): kind `must|preferred|knockout`, quote, normalized JSON. Rule extract always runs; cached by `jobs.qualifications_hash`. Knockouts compared to profile + answer bank (`matching/knockout.py`). Per-row verdicts in `track_jobs.fit.ledger`.

## Match highlights

`GET /track-jobs/{id}` also returns `match_terms`: short, named skills found in the posting, each with a verdict against the user's profile.

- **Vocabulary** (`taxonomy/skills.py`): concrete languages, frameworks, platforms, tools, databases, and products. Soft skills and generic practices stay out; they over-highlight prose and the ledger already covers them.
- **Evidence** (`matching/highlights.py`): a term is `met` when a profile skill matches (alias-aware, so `Postgres` and `PostgreSQL` agree), `partial` when only a qualification ledger verdict says so, and `gap` otherwise. Terms excluded by the Track are dropped.
- **Ranking**: matches first, then related, then gaps. Within a group, Track must-haves and qualification musts lead, then mentions near requirement language (`required`, `must`, `years`, `proficiency`), then raw mention count. Caps: 10 matches, 3 related, 8 gaps.
- **Safety**: only the curated labels, profile skill names, and short surface forms cross the API. Posting sentences are never echoed back through this path, and the detector works on sanitized `description_text` without calling an LLM.
- The web reader marks these terms inline (`<mark>`): a brand fill for profile matches, a pencil fill for related evidence, and a neutral fill for gaps. The chips above the posting pair each fill with a glyph and a word.

## API

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/v1/jobs` | Board list; `track_id`, `sort`, `include_not_eligible` |
| GET | `/api/v1/jobs/export.csv` | Current view CSV |
| GET | `/api/v1/track-jobs/{id}` | Drawer detail, qualifications, `match_terms` |
| POST | `/api/v1/track-jobs/{id}/triage` | shortlist / skip / hide / applied / restore |
| POST | `/api/v1/tracks/{id}/score` | Re-run funnel |
| GET | `/api/v1/tracks/{id}/relaxations` | Zero-result suggestions |
| POST | `/api/v1/hidden-companies` | Hide company |

Discovery `discover_track` calls `score_track_jobs` at the end (LLM top-N disabled inline for latency).

## UI

`/jobs` Reader: list · posting · fit panel. The posting shows inline skill highlights; a `Highlight matches` toggle (persisted in `localStorage`) turns the marks off without hiding the summary. The context panel has a collapsed **How the score is built** breakdown of `score_components`. Keyboard `j/k/s/x/o/?`. Track detail shows scored rows + link to board.

## Evals

- Ranking: `tests/evals/test_ranking_eval.py` (≥200 pairs) NDCG@20 / P@10 ≥ rule-only.
- Qual extract: `tests/evals/test_qual_extract_eval.py` (≥50) must/preferred ≥85%, knockout recall ≥95%.
