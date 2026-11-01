# Phase 3: Career Profile (scratchpad)

**Branch:** `phase/02-auth-tenancy-shell` (no commits or `main` exist yet, so Phase 3 builds on the uncommitted Phase 2 tree) · **Started:** 2026-11-01 · **Phase file:** `docs/phases/phase-03-career-profile.md`

## Plan (vertical slices)

1. [x] Profile core: migration 0008, models, CRUD for profile + sections + bullets, RBAC, audit, cross-tenant tests
2. [x] Documents: migration 0009, S3/MinIO (memory in tests), upload + presign/finalize, extract, sensitive-number strip, injection sanitize
3. [x] Parse: `ProfileExtract`, `run_structured`, confidence paths, draft in `documents.parsed`, confirm (append, once per doc), evals-lite
4. [x] Merge engine: fuzzy entity match, preview conflicts/additions, resolve API; confirm gated with `merge_required`
5. [x] Answer bank (canonical keys, variants, scope, approved, setup, RLS/audit)
6. [x] Voice profile (samples to style JSON, banned phrases)
7. [x] Profile interview (SSE, proposals)
8. [x] Frontend: onboarding step, parse review, profile page, interview drawer, answer bank, voice, documents
9. [x] Golden parsing set (≥15) + evals, docs (`architecture/profile.md`, route guides), E2E

## Open questions

- Phase 2 and 3 work are both uncommitted; user decides when to commit.

## Decisions

- Generic section registry for the simple profile sections (education, projects, certifications, languages, skills) to avoid seven copies of the same router.
- Parse uses `PromptedOutput(ProfileExtract)` so Gemini is not blocked by native JSON-schema state limits.

## Deviations from the phase file (also edit the phase file + prd.md)

- 

## Verification log

- [x] `pnpm run ci:quality` (EXIT:0; API 240 passed, evals-lite 25 passed)
- [x] Acceptance scenarios covered by API + E2E (`e2e/career-profile.spec.ts`)
- [x] Screenshots 375/820/1440 × light/dark in `docs/design/screenshots/phase-03/`
