---
name: ai-evals
description: Golden sets, fabrication checks, and how to add an eval when changing a prompt or model. Use whenever AI behavior changes.
---

# AI evals

- Evals live in `apps/api/tests/evals/` with golden inputs in `fixtures/` (synthetic profiles and postings only).
- **Two tiers**: `evals-lite` (deterministic checks and recorded model outputs, runs in CI) and full evals (live model, run on demand and before releases).
- **Always include**: a **fabrication check** for resume/answer/cover-letter prompts (every claim traceable to a profile fact; invented employer/metric/skill fails), an **injection fixture** for any prompt that reads untrusted text (output must ignore embedded instructions), and a **sensitive-field fixture** (no sensitive values leak into prompts/outputs).
- Adding an eval: write the failing case first, change the prompt, record the passing output, commit both. Note the prompt version id in the case.
- Track pass rate and cost per run; a drop blocks the change unless justified in the PR.
- Run: `pnpm run test:evals-lite` (CI), `pnpm run test:evals` (live).
