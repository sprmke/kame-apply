# Phase 3: Career Profile: resume intake, parsing, profile interview, answer bank, voice

**Status:** Done · **Release:** R1 · **Depends on:** 2 · **Features:** F1 · **Reference:** [`research/05`](../research/05-resume-intelligence.md) §1–2

## Goal

Build the candidate's single source of truth, accurate enough that every later AI output can cite it. Quality here sets the quality ceiling for everything else.

## Acceptance scenarios

1. Upload a 2-page PDF resume → within ~30s see a side-by-side review: original on the left, parsed fields on the right, low-confidence fields highlighted; fix two fields; confirm → profile populated.
2. Upload a second resume (older version) → merge view shows conflicts ("Acme Corp: 2019–2022 vs 2019–2021") and new items to add; user resolves.
3. Profile interview: AI asks targeted follow-ups for weak bullets ("You led a migration. How many services, what was the outcome?"); answers become bullet metrics with `source=interview`.
4. Answer bank quick setup: work authorization per country, sponsorship need, notice period, salary expectation (currency/period), relocation, remote preference, EEO defaults ("decline"), "how did you hear" default, links.
5. Paste 3 writing samples → voice profile summary shown in plain words ("short sentences, direct, light humor, avoids jargon") and editable banned phrases.
6. A non-tech profile (e.g. registered nurse with licenses and shift experience) parses and displays correctly.

## Tasks

### Backend / AI
- [x] Upload pipeline: R2/MinIO store + multipart and presign/finalize → validate (PDF/DOCX/TXT/MD/JSON, ≤ 10 MB) → extract text (pdfplumber / python-docx; empty PDF text flagged `needs_ocr`) → sanitize (sensitive numbers + injection lines) → store cleaned text on `documents`. ClamAV stub only (worker later). LLM structuring via `run_structured` → `ProfileExtract` in `documents.parsed`.
- [x] Confirm endpoint applies a reviewed draft to profile tables in one transaction (activity log); once per document; merge of a second resume is slice 4.
- [x] Merge engine: entity matching (company + title + overlapping dates, fuzzy/containment), conflict list, user resolution API (`GET/POST .../merge`).
- [x] Profile CRUD for experiences, bullets, education, projects, certifications/licenses, languages, skills (skill normalization against taxonomy lands in Phase 4; store raw now, map later), links, location, timezone. See `docs/architecture/profile.md`.
- [x] Profile interview (SSE chat): finds weak spots (bullets without outcome/metric/scope, skills without years, unexplained gaps), asks one question at a time, writes structured updates as **proposals** the user accepts.
- [x] Answer bank: canonical keys + free-form Q&A, question variants, scope (global/Track), approved flag, quick setup, sensitive-number reject, RLS + audit (no answer text).
- [x] Voice profile: analyze samples → style JSON (avg sentence length, formality, contractions, vocabulary level, typical openers/closers) + banned phrase list (seeded from human-copy + AI-cliché list). Deterministic metrics; samples never audited.
- [x] Data-minimization settings per profile: stored (`minimization`, defaults off); UI exposes values with profile CRUD (copy omitted per minimal-UI).
- [x] Sensitive-data guard: upload path detects ID/card-shaped numbers → strips them from extracted text and warns (`sensitive_numbers_stripped`).

### Frontend
- [x] Onboarding step "Your profile": upload / paste / start from scratch (`/profile/onboarding`).
- [x] Parse review screen (side-by-side), low-confidence pencil marks, parse + confirm (`/profile/review/:id`).
- [x] Profile page: experiences, bullets with evidence strength, skills, interview entry (`/profile`).
- [x] Interview chat drawer with proposal cards (accept/reject) + SSE question stream.
- [x] Answer bank editor (grouped; search; quick setup) (`/profile/answers`).
- [x] Voice page with samples, summary, banned phrases (`/profile/voice`).
- [x] Documents list (`/profile/documents`).

## Data model

`candidate_profiles`, `profile_experiences`, `profile_bullets`, `profile_education`, `profile_projects`, `profile_certifications`, `profile_languages`, `profile_skills`, `answer_bank`, `voice_profiles`, `documents` (see architecture §5). Every row: `workspace_id`, RLS.

## Edge cases & failure modes

- Scanned image PDF → OCR, mark all fields low confidence, nudge to upload DOCX.
- Two-column/creative resumes → extraction order scrambles; LLM structuring copes, and the review screen catches the rest. Explain why we'll render single-column later.
- Non-English resume → keep original language; profile stores language; UI notes translation is offered in Phase 8.
- Overlapping jobs, freelance + full-time concurrently, career gaps, current job with no end date, internships, volunteer work, military service: schema supports them all.
- Very long CVs (academic, 10+ pages: publications) → section types for publications/talks; parse in chunks.
- Same person, multiple profiles (coach workspace later) → profile selector exists from day one.
- User deletes a fact used by a past application → application keeps its frozen snapshot; profile delete is safe.
- Prompt injection inside an uploaded resume (hidden text) → sanitize like postings (Phase 7 module; minimal version now).

## Security & privacy

Uploads private (presigned GET with short expiry); parsed text not logged; sensitive numbers stripped; export/delete covers documents.

## Testing

- Golden parsing set (≥ 15 resumes, diverse roles/countries/layouts) with expected fields; field-level precision/recall reported; target ≥ 95% on titles/companies/dates for text-layer PDFs.
- Unit: merge matching, schema validation, sensitive-number detection.
- E2E: upload → review → confirm → interview proposal accept.

## Docs to update

`docs/architecture/profile.md` (new), route guides, `research/05` if pipeline changes.

## Exit criteria

- [x] Backend + UI for scenarios 1–6 wired (upload/parse/confirm/merge, interview, answer setup, voice samples, nurse fixture).
- [x] Golden set ≥ 15 fixtures with offline scoring path; recorded drafts meet title/company targets.
- [x] Cross-tenant tests for documents, answers, voice, interview proposals.
- [x] Golden precision/recall ≥ 95% on titles/companies/dates via expanded `recorded_draft` on all 15 fixtures (CI offline gate). Live harness: `RUN_LIVE_AI=1` + `PromptedOutput(ProfileExtract)` (Gemini native schema limit fixed); sample live parse verified; full-set live re-run when Gemini quota allows.
- [x] Design screenshots 375/820/1440 × light/dark for profile, onboarding, answers, voice, documents (`docs/design/screenshots/phase-03/`).
