# IND-7: Resume, tailor, letters (scratchpad)

**Branch:** `ind/01-pack-foundation` · **Started:** 2026-11-13 · **Plan:** §9.4

## Shipped

- `build_from_profile` now emits certifications, projects, and languages, and orders sections by `pack.resume.section_order`.
- Pack `section_titles` relabel Kitchen skills, Signature dishes and menus, and Food safety certificates.
- `create_base` records the pack template id (for example `chef`) when the caller leaves the default.
- `profile_extract` v2 with pack brief and a no-invented-certificate rule; eval fixture/version tests updated.
- `job_fit`, `resume_critique`, `resume_lens`, `resume_tailor_review`, and `cover_letter` are v2 and receive the pack brief plus bullet guidance at runtime.
- Tests: pack order/titles, prompt brief presence, existing resume/parse tests.

## Limits

- RenderCV still uses its default visual template; the pack template id is recorded but not a separate visual design yet.
- Tailoring fabrication evals for chef profiles remain a live-AI task.

## Verification

- `pnpm run ci:quality` passed (591 API tests, 3 skipped; web 18; extension 9; ui 21; evals-lite 103).
- `tests/test_industries_remaining.py` covers detection, search plan, custom pack draft/accept, advice, gaps, interview, safety fees, resume order, and prompt briefs.
- Registry/i18n tests cover every extra pack label, family, and credential.
