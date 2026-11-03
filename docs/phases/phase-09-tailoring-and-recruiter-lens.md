# Phase 9: Per-job tailoring, Recruiter Lens, cover letters

**Status:** Done (not merged) · **Release:** R1 (MVP centerpiece) · **Depends on:** 8 · **Features:** F7 (tailor), F18 · **Reference:** [`research/07`](../research/07-how-recruiters-find-and-screen.md), [`research/05`](../research/05-resume-intelligence.md) §6

## Goal

For a job the user really wants, produce the strongest **truthful** resume for that posting: one that a 2026 ATS AI grades as a strong fit and that a human recruiter understands in 7 seconds. Show the predicted improvement and the honest gaps.

## Acceptance scenarios

1. From a job drawer, **Tailor resume** → streamed progress → split view: qualifications with Fit & Gap verdicts **before → after**, overall grade (e.g. C → A-), resume diff, preview. Under 60 s.
2. Each must-have the user has evidence for is evidenced in an experience bullet using the posting's terminology (and acronym form when the user has it), and the top 3–5 appear in the summary or first bullets of the latest role.
3. A must-have with no evidence shows as a gap with options (address adjacent experience honestly / add a missing fact to the profile if it's true / consider skipping). It's never inserted.
4. Knockout panel: predicted pass/fail for authorization, location, years, degree, language, salary. A fail suggests not applying.
5. Accept → resume version frozen and attached to a new `application` (status `ready`); PDF/DOCX pass the parse gate.
6. Optional cover letter (150–250 words) in the user's voice, citing 2–3 real matches and a company-specific reason sourced from the posting/company page; no stock phrases.
7. Re-tailoring after editing the profile creates a new version; the application keeps the version history and which one was sent.

## Tasks

### Recruiter Lens (`resumes/lens.py`)
- [x] Input: resume version (rendered → re-parsed, i.e. what an ATS would see) + `job_qualifications`.
- [x] Per-qualification verdict with quoted evidence and evidence location (role, dates → computed years, recency).
- [x] Overall grade A–D modeled on requirement-by-requirement graders; weights: must > preferred; knockouts separate.
- [x] Skim analysis on the top third of page 1 (title/company/dates/summary visibility of top must-haves).
- [x] Authenticity checks: banned phrases, generic claims, inconsistencies with profile; LinkedIn consistency if the user pasted LinkedIn text (Phase 18 deepens).
- [x] Lens report stored on the version; shown as "simulation" with stated limits.

### Tailoring workflow (`tailor_application` DBOS)
- [x] Steps: load → Lens(before) → plan ops per research/05 §6 → drafter → fresh-context reviewer ("skeptical recruiter for this role") → revise once → truthfulness verifier → length budget → render → parse gate → Lens(after) → await accept.
- [x] Terminology mapping: posting term ↔ profile skill via taxonomy aliases (use the posting's surface form when it's the same skill).
- [x] Guard against keyword stuffing: per-term frequency cap, no hidden text, skills section limited to evidenced skills.
- [x] Cover letter generator using voice profile + verifier: `cover_letter.v1` drafts from evidence quotes only, the draft is checked sentence by sentence against profile evidence (numbers, entities, banned phrases, 150-250 words), and any failure falls back to the deterministic letter.
- [x] Batch tailoring for shortlisted jobs (autonomy `prepare` in Phase 10) with per-run budget. *(service ready; batch deferred to Phase 10)*

### Frontend (blueprint §3.5)
- [x] Tailor view (desktop 3-pane; mobile tabs), grade badge before/after, qualification checklist, diff accept/reject, gap actions, knockout panel, cover letter tab, accept & create application.

## Edge cases & failure modes

- Posting with 30+ "requirements" (wish lists) → weight musts; Lens notes "long wish list: humans rarely expect all".
- Requirement phrased as years in a specific tool the user used but dates are unclear → ask the user (profile proposal) instead of assuming.
- Title mismatch → use the honest equivalence pattern from research/07, only if the user confirms it's true.
- Non-English posting → tailor in posting language only if the user enables translation; facts unchanged.
- Very similar jobs at the same company → reuse a tailored version with diff; warn about per-company caps (Phase 18).
- Tailoring cost spikes → budget guard; bulk tier for Lens; premium tier only on explicit "deep tailor".
- Job closed while tailoring → finish, but mark application "job closed".

## Testing

- Eval: 30 job × profile pairs → fabrication 0; Lens grade improves or stays (never decreases without explanation); must-have evidenced coverage ≥ 95% of evidence-available musts; human blind A/B on 10 pairs (tailored vs base) prefers tailored ≥ 80%.
- Unit: Lens grading determinism given fixed LLM outputs; stuffing caps; verifier rules.
- E2E: tailor → accept → application created → files download.

## Docs to update

`docs/architecture/resumes.md` (tailoring + Lens), PRD F18 if behavior changes, route guides.

## Exit criteria

- [x] Scenarios 1–7 pass; eval targets met in CI (`test:evals` / `test:evals-lite`).
- [ ] Michael applies to ≥ 5 real jobs with tailored resumes (dogfood; owner).
