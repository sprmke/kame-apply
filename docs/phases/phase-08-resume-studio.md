# Phase 8: Resume Studio: critique, market insights, improved base resume, rendering + parse gate

**Status:** Done (not merged) · **Release:** R1 · **Depends on:** 6 · **Features:** F7 (critique, research, improve, render), F18 (parse check) · **Reference:** [`research/05`](../research/05-resume-intelligence.md), [`research/07`](../research/07-how-recruiters-find-and-screen.md)

## Goal

Tell the user exactly what's wrong with their resume for each Track, backed by evidence from real postings, and give them an improved, parse-safe base resume per Track, with no invented facts.

## Acceptance scenarios

1. "Critique my resume" on a Track → category scores (research/05 §3) + top 5 fixes ranked by impact, each linked to a line, within ~30 s (streamed).
2. Market insights for the Track: top 25 skills with frequency and trend, color-coded have-shown / have-not-shown / adjacent / gap, sample size + confidence, salary range, common titles. Low-sample warning when < 30 postings.
3. "Improve for this Track" → proposed base resume as a diff (summary, bullets, skills order, section order) with reason + evidence per change; user accepts some, rejects others; final PDF + DOCX render.
4. Every exported file passes the **parse round-trip gate**; a deliberately broken template fails it with a clear message (dev test).
5. Fabrication check: on the golden set, 0 generated claims lack evidence; numbers in output all exist in the profile.
6. Skim view highlights the 7-second zone; Parse view shows what an ATS extracts.

## Tasks

### Backend / AI
- [x] Resume content model (`ResumeContent`: header, summary, sections with items, each line with `evidence_refs`), stored in `resume_versions.content`.
- [x] Critique engine: deterministic checks (length, dates, tense, banned phrases, quantification ratio, heading names) + LLM rubric scoring with line-level findings (structured output); prioritize by impact model (market-fit gaps × visibility).
- [x] Market insights job (`compute_market_insights` per Track, nightly + on demand): aggregation over `job_qualifications`/skills of matched jobs (30/90d), trends, salary distribution, titles, certifications, years-required distribution; compare to profile evidence.
- [x] Optional AI web research (budgeted, cited, labeled secondary). *(stub `secondary_research` field; live research deferred)*
- [x] Generator: proposal operations (rewrite/reorder/add-to-skills/summary/condense) → **truthfulness verifier** (deterministic: numbers, entities, dates, skill evidence; LLM: claim-support check) → rejected ops → gaps list.
- [x] Profile → resume propagation: profile edits create suggestions on affected resume versions.
- [x] Rendering: RenderCV/Typst templates (3–4, single-column, A4/Letter), DOCX builder, plain text; locale date formats; file naming. *(reportlab fallback when RenderCV absent)*
- [x] **Parse round-trip gate**: extract text (pdfplumber + pypdf), re-parse with our structuring model **and** a rule-based parser; compare fields + order; fail with diagnostics.
- [x] Translation (optional): render resume in another language for Tracks in non-English markets, same facts, flagged for user review. *(deferred; not required for exit)*

### Frontend (blueprint §3.4)
- [x] Resume Studio: base resumes per Track, critique view, diff editor (accept/reject per change, all), inline "ask me for a metric" prompts that write back to the profile, live preview (PDF.js), Skim view, Parse view, template picker, downloads, version history. *(PDF.js deep preview deferred; download links + skim/parse ship)*
- [x] Market insights page with charts (follow `dataviz` skill; accessible colors; table fallback).

## Edge cases & failure modes

- Very junior profile (few bullets) → critique focuses on projects/education/skills evidence; no padding.
- Career changer → emphasize transferable evidence honestly; market gaps shown with learning suggestions (P2 hook).
- Many Tracks with conflicting emphasis → separate base resumes; shared profile.
- User edits the resume text directly (not via profile) → allowed; the edited line loses evidence refs → verifier flags "unverified line" and asks to link it to a fact or save it as a new fact.
- Page overflow → cut by relevance, never shrink fonts below template minimums.
- Countries expecting photo/DOB (DE, JP, parts of Asia/ME) → template option driven by Track setting, off by default.

## Testing

- Golden set (research/05 §8) across roles/countries; fabrication = 0; parse gate 100%; critique precision spot-check by human (5 samples/phase change).
- Visual regression on templates (PDF → PNG snapshots).
- E2E: critique → improve → accept → download.

## Docs to update

`docs/architecture/resumes.md` (new), prompt registry entries, route guides.

## Exit criteria

- [x] Scenarios 1–6 pass; golden-set gates green in CI (`test:evals`).
