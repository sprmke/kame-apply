# Phase 6: Qualification extraction, matching & ranking, job research board

**Status:** Done · **Release:** R1 · **Depends on:** 5 · **Features:** F5, F6 · **Reference:** [`research/07`](../research/07-how-recruiters-find-and-screen.md) §2(C,D)

## Goal

For every Track, show the jobs most worth the user's time, with honest, explainable reasons, and make triage fast. Matching mirrors how employer screeners evaluate: requirement by requirement.

## Acceptance scenarios

1. Track job list sorted by match: each row shows score, eligibility, salary fit, risk placeholder, and 2–3 reason chips.
2. Job drawer: qualifications list (must / preferred / knockout) with verdicts vs profile (met / partial / not evidenced / not met) and quotes; eligibility verdict with the posting quote ("Must be based in the US").
3. Keyboard triage of 30 jobs in under 3 minutes (j/k/s/x/o); skip reasons recorded.
4. After skipping 10 jobs for "too junior", similar jobs rank lower in that Track.
5. Zero-result Track shows ranked relaxation suggestions ("Remove salary floor: +42 jobs").
6. CSV export of the current view.

## Tasks

### Qualification extraction (global, once per job)
- [x] Rule extract (+ optional LLM bulk later) writes `job_qualifications`: kind (must/preferred/knockout), normalized skill/years/degree/license/language/location/authorization; quotes as evidence. Cached by content hash; re-run only on content change.
- [x] Knockout predictor: compares knockout qualifications with answer bank / profile (work auth, location, years, degree, license, language).

### Ranking funnel (per Track, per job)
- [x] Stage 1 **hard filters** (compiled criteria + knockouts → `not eligible` hidden by default, viewable).
- [x] Stage 2 **rule score**: title/occupation match, must-skill coverage, seniority fit, salary fit, freshness boost (posted < 72h), location/timezone fit, company preferences.
- [x] Stage 3 **semantic**: fastembed (or hash embedder in CI) for job + Track-profile vector; cosine; pgvector HNSW index.
- [x] Stage 4 **LLM fit** for top N when AI configured (budget-aware); else `ai_review_paused`.
- [x] Final score 0–100 with per-Track weights; store components for explanation.
- [x] Feedback learning: skip reasons and shortlist actions adjust per-Track weights (bounded; never hides jobs entirely).
- [x] Re-score triggers: criteria change, discovery complete (`score_track_jobs`).
- [x] Relaxation suggester: for each active filter, count jobs gained if relaxed.

### Board UX (blueprint §3.2)
- [x] Track Jobs section + global Jobs page; filters; sorting; reason chips.
- [x] Job drawer: header, why-match, qualifications with verdicts, description, company other roles, actions (shortlist, skip w/ reason, mark applied, open original).
- [x] Keyboard shortcuts + help; CSV export.
- [ ] Mobile swipe cards (deferred; keyboard + tap triage ships). Virtualized table deferred until volume needs it.

## Edge cases & failure modes

- Postings with no explicit qualifications → `few_stated_requirements`; don't over-score.
- Over-qualification → seniority component penalizes and can explain via reasons.
- Same job in multiple Tracks → applying marks `applied_elsewhere` on siblings.
- Embedding model version on `jobs.embedding_model`; hash fallback in tests.
- LLM budget / unset → stages 1–3 with `ai_review_paused`.
- Language knockout via fluent/native patterns.

## Testing

- Ranking eval ≥200 pairs: NDCG@20 and P@10 ≥ rule-only baseline.
- Qual extract eval ≥50: classification ≥85%, knockout recall ≥95%.
- Unit: rule components, relaxation, feedback bounds, extract. API: score/board/triage/CSV/cross-tenant. E2E: jobs page + shortcuts.

## Docs to update

`docs/architecture/matching.md`, route guides (`jobs.md`).

## Exit criteria

- [x] Scenarios 1–6 covered (API + UI + evals); eval targets met.
- [ ] Owner dogfood: top-20 on real Tracks "mostly worth opening" (confirm after using the board on personal data).
