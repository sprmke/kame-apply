# Career Profile

The candidate's single source of truth. Every later AI output cites facts stored here (PRD P1). Owned by `apps/api/app/profiles/`.

## Data model

### Profiles and facts (migration 0008)

`candidate_profiles` holds one row per person in a workspace; the first one created is the default (`is_default`, unique per workspace). Fact sections hang off a profile: `profile_experiences`, `profile_projects`, `profile_bullets`, `profile_education`, `profile_certifications` (kind `certification` or `license`), `profile_languages`, `profile_skills`.

- Every row carries `workspace_id` with forced RLS (`tenant_isolation` policy). The read-only dev role has no access.
- Every section row has `do_not_use`, `confidential`, `sort_order`, and `source` (`parsed`, `interview`, `user`).
- A bullet belongs to exactly one experience or project (check constraint), and that parent must belong to the same profile (checked in the service).
- Deleting a profile or a parent cascades to its sections. Applications keep frozen snapshots (Phase 11), so deletes are safe.
- `minimization` on the profile (photo, date of birth, full address) defaults to all off.
- Skill names are stored raw; mapping to the taxonomy lands in Phase 4.

### Documents (migration 0009)

`documents` stores upload metadata and cleaned extracted text. File bytes live in object storage under `ws/<workspace_id>/profiles/<profile_id>/documents/<id>/...` (never in Postgres).

| Column | Notes |
| --- | --- |
| `kind` | `resume_upload`, `portfolio`, `generated`, `paste` |
| `status` | `pending` (presigned, not finalized), `ready`, `failed` |
| `extracted_text` | Sanitized plain text for the LLM parse step |
| `parsed` | `ProfileExtract` draft JSON (null until parse) |
| `parse_quality` | Prompt version, provider/model, truncation, low-confidence paths, `confirmed_at` |
| `warnings` | Codes: `sensitive_numbers_stripped`, `injection_lines_removed`, `needs_ocr`, `extract_failed`, `text_truncated`, `low_confidence_fields` |

Upload limits: PDF / DOCX / TXT / MD / JSON, max 10 MB. Workspace `max_storage_mb` is enforced on upload. ClamAV is a no-op stub until the worker lands; Tesseract is not required yet (empty PDF text layer sets `needs_ocr`).

### Answer bank (migration 0010)

`answer_bank` stores reusable form answers per profile. Sensitive-class numbers (SSN/card-shaped) are rejected on write. Audit rows store key, scope, country, approved, and field names only — never answer text.

| Column | Notes |
| --- | --- |
| `key` | Lowercase snake_case slug. Canonical catalog in `answer_keys.py` (work auth, sponsorship, notice, salary, relocation, remote, EEO, how heard, links). Free-form keys allowed. |
| `country` | Optional ISO 3166-1 alpha-2. Required for `work_authorization`; forbidden on other canonical keys. |
| `question_variants` | Phrasings that should resolve to this answer (semantic match lands in Phase 12). |
| `answer` / `answer_json` | Plain text is canonical; JSON holds structured extras (salary amount/currency/period). |
| `scope` | `global` or `track`. Track scope requires `track_id` (FK to `tracks` lands in Phase 4). |
| `approved` | Apply engine / autofill use approved answers only. |

Unique slot: `(profile_id, key, scope, country, track_id)` with NULLs coalesced. Quick setup (`POST .../answers/setup`) seeds missing canonical rows (work auth per requested countries, EEO decline defaults pre-approved, link URLs copied from the profile when present) and never overwrites existing answers.

### Voice profile (migration 0011)

One `voice_profiles` row per profile. Pasted writing samples live in `samples` JSONB (never logged). `style` holds deterministic metrics: avg sentence length, formality, contraction rate, vocabulary level, openers/closers, and a plain-language `summary`. `banned_phrases` seeds from human-copy bans + AI clichés; the user can edit the list.

| Route | Action |
| --- | --- |
| `GET /{id}/voice` | get or create empty voice row (seeded banned list) |
| `PUT /{id}/voice/samples` | replace samples (`analyze` default true) |
| `POST /{id}/voice/analyze` | recompute style from stored samples |
| `PATCH /{id}/voice` | edit `banned_phrases` and/or `summary` |

### Interview (migration 0012)

`profile_proposals` holds draft updates from the profile interview. Gaps are computed deterministically (weak bullets, skills without years, unexplained career gaps). A turn stores a pending proposal; accept writes into fact tables with `source=interview`. SSE `GET .../interview/stream` types the next question (`gap` → `token`* → `done`). Audit never stores question or answer text.

| Route | Action |
| --- | --- |
| `GET /{id}/interview/gaps` | list weak spots |
| `GET /{id}/interview/stream` | SSE next question |
| `POST /{id}/interview/turns` | answer a gap → pending proposal |
| `GET /{id}/interview/proposals` | list (`status` filter) |
| `POST /{id}/interview/proposals/{pid}/accept` | apply to profile |
| `POST /{id}/interview/proposals/{pid}/reject` | discard |

## Parse and confirm

1. `POST .../documents/{id}/parse` runs `run_structured` with prompt `profile_extract.v1` (tool-less). Resume text is wrapped in `<<<UNTRUSTED_RESUME_TEXT>>>` delimiters. Output is validated as `ProfileExtract`, scrubbed again for sensitive numbers and injection phrases, then stored in `documents.parsed`. Long text is truncated at 60k characters with a warning. Requires a ready document, non-empty extract, an AI credential, and no prior confirm.
2. Review UI (slice 8) edits the draft client-side. Low-confidence paths (`confidence < 0.6`) are listed in `parse_quality.low_confidence_paths`.
3. `POST .../documents/{id}/confirm` applies the draft when the profile has **no** section facts yet. If the profile already has facts, confirm returns `409 merge_required`.
4. **Merge (second resume):** `GET .../documents/{id}/merge` previews matches, field conflicts, additions, and header conflicts. Matching is deterministic (normalized org/title, fuzzy similarity, date overlap; org containment for short vs long names). Blank fields auto-fill; differing values become conflicts. `POST .../documents/{id}/merge` applies resolutions (`keep_existing` | `take_incoming` | `merge` with per-field actions), addition add/skip, and bullet add/skip, then marks the document confirmed (`parse_quality.merged`).

Evals-lite: `apps/api/tests/evals/` (`pnpm run test:evals-lite`). Golden set (≥15) under `tests/evals/fixtures/golden/` with offline `recorded_draft` scoring (≥95% company/title/date). Live scoring: `RUN_LIVE_AI=1 uv run pytest apps/api/tests/evals/test_golden_set.py::test_live_golden_precision_recall_target`. Parse uses `PromptedOutput(ProfileExtract)` so Gemini is not blocked by native JSON-schema state limits.

## API (all under `/api/v1/profiles`, workspace-scoped)

| Route | Action |
| --- | --- |
| `GET /`, `POST /` | list (default first), create |
| `GET /{id}` | profile with every section |
| `PATCH /{id}`, `DELETE /{id}` | update, delete (deleting the default promotes the oldest remaining) |
| `GET/POST /{id}/{section}`, `PATCH/DELETE /{id}/{section}/{item_id}` | sections: `experiences`, `projects`, `bullets`, `education`, `certifications`, `languages`, `skills` |
| `GET/POST /{id}/documents` | list; multipart upload (validate, store, extract, sanitize) |
| `POST /{id}/documents/presign` | create pending row + short-lived PUT URL |
| `POST /{id}/documents/{doc_id}/finalize` | read object, extract, sanitize |
| `GET /{id}/documents/{doc_id}` | metadata + extracted text + draft |
| `GET /{id}/documents/{doc_id}/download-url` | short-lived GET URL after scope check |
| `POST /{id}/documents/{doc_id}/parse` | LLM structure → `parsed` draft |
| `POST /{id}/documents/{doc_id}/confirm` | first-time apply to empty profile (`{ draft?, apply_header }`); else `merge_required` |
| `GET /{id}/documents/{doc_id}/merge` | merge preview (conflicts, matches, additions) |
| `POST /{id}/documents/{doc_id}/merge` | resolve merge and confirm |
| `DELETE /{id}/documents/{doc_id}` | delete row and object |
| `GET /{id}/answers/keys` | canonical key catalog |
| `GET /{id}/answers` | list (`key`, `scope`, `country`, `track_id`, `approved`, `q`) |
| `POST /{id}/answers` | create |
| `POST /{id}/answers/setup` | seed missing canonical rows (`countries`, `include_links`) |
| `GET/PATCH/DELETE /{id}/answers/{answer_id}` | read, update, delete |

Reads need `data.read` (all roles); writes need `data.write` (owner, admin, member). A profile is capped at 10 per workspace.

Patching re-validates the merged row against the create schema, so cross-field rules (end date after start, a current role has no end date) hold on edit.

`evidence_strength` on a bullet is computed server-side: `strong` with a metric, `ok` with any number in the text, else `weak`.

## Audit

Events: `profile.created|updated|deleted`, `profile.<section>.created|updated|deleted`, `document.created|ready|failed|deleted|parsed|confirmed|merged`, `answer.created|updated|deleted`, `voice.created|samples_updated|analyzed|updated`, `interview.proposal_created|accepted|rejected`. They store ids, kinds, mime, sizes, warning codes, prompt version, counts, field names, and answer/voice/proposal metadata, never resume text, file bytes, answer text, writing samples, or interview replies.

## Object storage env

| Variable | Local default | Notes |
| --- | --- | --- |
| `S3_ENDPOINT_URL` | `http://127.0.0.1:9100` | MinIO; set to the R2 endpoint in prod |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | compose credentials | |
| `S3_BUCKET` | `kame-apply` | Created on API startup when missing |
| `S3_REGION` | `auto` | |

Tests use an in-memory store (`ENVIRONMENT=test`).
