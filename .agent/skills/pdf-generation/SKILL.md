---
name: pdf-generation
description: Resume PDF/DOCX rendering with RenderCV (Typst) and python-docx, plus the parse round-trip gate. Phase 8.
---

# PDF generation

Read `docs/phases/phase-08-resume-studio.md` and `docs/research/05-resume-intelligence.md` first.

- PDF via RenderCV/Typst from a structured resume document; DOCX via python-docx. ATS-safe: single column, real text layer, standard headings, no text in images.
- Every rendered file is parsed back (text extraction) and compared to the source facts; a mismatch fails the render gate.
- Files go to R2 by key, never into Postgres. Fixtures live under `apps/api/tests/fixtures/`, never real resumes.
- Follow `truthful-content.mdc`: render only accepted, evidence-backed content.
