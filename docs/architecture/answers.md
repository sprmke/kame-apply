# Answer Desk

Phase 12. PRD F9 · research/04 §5 · UX blueprint §3.7.

## Flow

Paste (or extension-captured) form text → split into questions → resolve each:

1. **AI restriction** (multilingual patterns) → no draft; fact notes only ("Write this yourself").
2. **AI-use disclosure** → truthful stance from `voice_profiles.ai_use_stance` (or default).
3. **Answer bank** (canonical key / variants / embeddings) → verbatim, labeled from bank.
4. Else **draft** from Career Profile facts + voice + banned-phrase strip + length fit.

Tone controls re-run the drafter (`shorter` / `more_specific` / `more_casual` / `more_formal`). Save to bank stores an approved row for the next similar question.

## Tables

| Table | Role |
| --- | --- |
| `answer_desk_sessions` | Paste + optional `application_id`; `page_restricted` |
| `answer_desk_items` | Per question: constraints, draft, evidence, restriction flags |

RLS on `workspace_id`.

## API

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/answer-desk/parse` | Split + resolve |
| POST | `/answer-desk/parse/stream` | SSE session then items |
| POST | `/answer-desk/detect` | Restriction probe (extension) |
| GET | `/answer-desk/sessions/{id}` | Reload |
| POST | `/answer-desk/items/{id}/tone` | Redraft |
| PATCH | `/answer-desk/items/{id}` | Manual edit |
| POST | `/answer-desk/items/{id}/save-to-bank` | Persist |
| GET | `/applications/{id}/answers` | Attached desk items |
| PUT | `/profiles/{id}/ai-use-stance` | Truthful AI-use answer |

## Evals

`tests/evals/fixtures/answer_desk/restriction_corpus.jsonl` (≥80 restricted phrasings, 6 languages). Gate: recall ≥ 98%, zero false positives on clear negatives. Fabrication/banned lint on 30 synthetic drafts.

## Mutations → audit

`answer_desk.parsed`, `answer_desk.saved_to_bank`, `answer_desk.stance_updated`.
