# Phase 04: Tracks & criteria builder + taxonomy (scratchpad)

**Branch:** `phase/02-auth-tenancy-shell` (uncommitted Phases 1–4 tree) · **Started:** 2026-11-01 · **Phase file:** `docs/phases/phase-04-tracks-and-criteria.md`

## Plan (vertical slices)

1. [x] Slice A: `CriteriaV1` + summary/diff/merge/validate + unit tests
2. [x] Slice B: Global taxonomy tables, curated seed, refresh script, title/skill normalizers
3. [x] Slice C: Tracks + track_criteria (RLS), CRUD/duplicate/archive/reorder, templates seed
4. [x] Slice D: NL compiler (PromptedOutput) + invent-guard + eval fixtures (≥60)
5. [x] Slice E: Geocode cache + currency/period normalization
6. [x] Slice F: Web UI (list, criteria builder, settings placeholders) + i18n + route guides
7. [x] Slice G: Screenshots 375/820/1440 × light/dark, `ci:quality`, exit criteria

## Open questions

- Full ESCO/O*NET dumps are large; CI uses curated seed; refresh script loads full dumps offline.
- Title embeddings: trigram + aliases on request path; vector column filled by refresh when enabled.

## Decisions

- Taxonomy is global (no RLS); app role SELECT-only; refresh runs as owner.
- Compiled filters are versioned JSON predicate descriptors (not raw SQL strings).
- NL compiler uses PromptedOutput (same Gemini constraint as profile extract).
- Preview count stays the Phase 5 placeholder string until discovery exists.
- Vue Query `useQuery` returns plain refs: templates must use computed `.value` helpers (never raw `query.isLoading` in template).

## Deviations from the phase file (also edit the phase file + prd.md)

- Company include/exclude in More filters are comma-separated free text (no company directory autocomplete until discovery/company directory exists).
- Country filter is region presets + location place text (full country multi-select deferred with Phase 5 geo UX).

## Verification log

- [x] Tracks + criteria evals: 70 passed (`test_tracks.py` + `test_criteria_compile.py`)
- [x] E2E `e2e/tracks.spec.ts` (create, more filters, settings, duplicate/archive, checklist)
- [x] Screenshots 30 under `docs/design/screenshots/phase-04/`
- [x] `pnpm run ci:quality` (EXIT:0; API 316 passed; evals-lite 88 passed)
- [x] Acceptance scenarios 1–5 covered by API + E2E (NL compile mocked in API; live Gemini optional)
