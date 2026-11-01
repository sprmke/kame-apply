# Research 05: Resume intelligence (parse, critique, research, improve, tailor, render)

**Researched:** 2026-10-28 · Feeds into Phases 3, 8, 9. Pairs with [`07-how-recruiters-find-and-screen.md`](./07-how-recruiters-find-and-screen.md).

## 1. Truthfulness architecture (why fabrication is structurally hard)

- The **Career Profile** is the only source of facts. Every generated resume line stores `evidence_refs[]` → profile bullet/experience/skill ids.
- Generation is two-pass: (1) LLM proposes changes as structured operations (`rewrite bullet X`, `reorder`, `add skill Y to skills section`, `summary`), each with evidence refs and reason; (2) a **verifier** (separate prompt + deterministic checks) rejects any operation whose claim isn't supported: new numbers not in evidence, new employers/titles/dates, skills with no evidence, degree changes. Rejected operations become "gaps".
- Metrics: the AI may suggest *asking the user* for a metric ("How many users did this serve?") but never invents one. The profile interview captures real numbers.
- Users can mark facts "do not use" (e.g. old jobs) and "confidential" (rename client as "a Fortune 500 retailer").

## 2. Parsing uploads (Phase 3)

Pipeline: file validation → text extraction (pdfplumber for PDFs with text layer; python-docx for DOCX; markitdown as a general fallback; OCR via Tesseract only if no text layer, flagged low-confidence) → LLM structuring into the profile schema (Pydantic, strict) → per-field confidence → **user confirmation UI** (side-by-side original vs parsed; nothing enters the profile unconfirmed). Multiple uploads merge with conflict resolution (same company with different dates → ask).

Also import: LinkedIn "Save to PDF" profile export, JSON Resume, plain text paste.

## 3. Critique rubric (Phase 8)

Scored categories (each 0–5 with line-level findings and fixes). Rubric seeds: kame-hunt `docs/03-resume-review.md` + kame-pick recruiter scoring rubric + research/07.

| Category | Checks |
| --- | --- |
| Parseability | Single column, standard headings, contact in body, date formats, text layer, no tables/images/icons; parse round-trip result |
| Targeting | Summary names target role + top must-haves for the Track; title alignment |
| Evidence & impact | Bullets: action + scope + outcome; quantified where possible; no responsibilities-only bullets; ≤ 2 lines |
| Market fit | Coverage of the Track's top demanded skills (from market insights): shown in experience, only listed, or missing |
| Recency & relevance | Most relevant evidence in recent roles; old/irrelevant roles condensed |
| Clarity & concision | Length vs experience; jargon; passive voice; filler; repeated verbs |
| Authenticity | Stock AI phrases ("results-driven", "spearheaded synergies", "passionate about leveraging"), vague claims, inconsistency with LinkedIn |
| Consistency & polish | Tense, punctuation, date formats, capitalization of tech names (JavaScript, PostgreSQL) |
| Human skim | Top-third check (research/07 §F) |

No single magic "ATS score". Show the category scores, and the top 5 fixes ranked by expected impact.

## 4. Market research per Track (Phase 8)

- **Data:** all jobs matched to the Track in the last 30/90 days (deduped), with `job_qualifications` + skills mapped to ESCO skills.
- **Compute:** skill frequency (must vs preferred), co-occurrence clusters, trend (30d vs prior 30d), seniority split, common titles, salary distribution (posting + Adzuna), certifications, years-of-experience requirements distribution, top hiring companies.
- **Compare** with the profile: `have + shown`, `have + not shown on resume` (quick wins), `adjacent` (have related skill), `gap`.
- **Optional AI web research** (budgeted): summarize recent trend articles for the role with citations, labeled as secondary to the data.
- **Small samples:** under 30 postings → show "low confidence" and widen the window/criteria suggestion.

## 5. Improve / generate base resume per Track (Phase 8)

From profile + market insights + critique → proposed base resume for the Track → diff view per section with reasons and evidence → accept/reject per change → render. Users can maintain several base resumes (one per Track) derived from one profile; editing a profile fact propagates as suggestions to all resumes.

## 6. Per-job tailoring (Phase 9, MVP)

1. Load `job_qualifications` (must/preferred/knockout) for the posting.
2. **Lens before:** Fit & Gap per qualification on the base resume.
3. Plan: for each must/preferred qualification with profile evidence not yet surfaced → surface it (rewrite bullet in posting terminology, move it up, mention in summary); for qualification with only adjacent evidence → honest bridging phrasing ("built REST APIs in FastAPI; familiar with Django ORM concepts" only if true); for gaps → list.
4. Keep the length budget: cut least relevant bullets (relevance × uniqueness), not font size.
5. Verify (truthfulness verifier), render, **parse round-trip**, **Lens after**.
6. Present: grade before → after, qualifications newly evidenced, gaps, diff. User accepts; version is frozen to the application.
7. Cover letter (optional): 150–250 words, voice profile, 2–3 specific matches + why this company (from the posting/company page, never invented), no clichés.

Drafter → reviewer loop (from AI Job Search): a second, fresh-context review prompt critiques the draft as "a skeptical recruiter for this role", and the drafter revises once. Bounded to one loop for cost.

## 7. Rendering (Phase 8)

- **RenderCV (Typst)** from our content JSON → PDF; 3–4 templates, all single-column, ATS-safe; locale-aware dates; A4/Letter by country.
- DOCX via python-docx with the same structure (some ATS/humans prefer DOCX).
- File naming: `Firstname-Lastname-Target-Role.pdf`.
- Optional plain-text version for paste-only forms.
- **Gate:** parse round-trip must pass (name, email, phone, each employer/title/date, section order) before download/attach.

## 8. Evaluation (quality assurance for AI features)

- Golden set: 20+ anonymized resumes across roles/countries/seniority (incl. non-tech: nurse, chef, accountant, warehouse) + 50 job postings.
- Automated checks: fabrication rate (claims without evidence) must be 0; parse round-trip 100%; Lens grade before vs after; length budget respected; banned-phrase count.
- Human spot review each phase that changes prompts (5 samples, checklist).
- Prompts are versioned in a prompt registry; changes run the eval suite in CI (`pytest -m eval`, uses a cheap model or recorded responses).
