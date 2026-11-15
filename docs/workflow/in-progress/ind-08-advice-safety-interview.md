# IND-8: Advice, safety, interview (scratchpad)

**Branch:** `ind/01-pack-foundation` · **Started:** 2026-11-13 · **Plan:** §9.5, §5.2 safety

## Shipped

- Gap suggestions use `pack.profile.gap_actions` (short course, stage, trial shift) before the generic resource list.
- `Get found` checklist comes from `pack.profile.found_checklist`; the Be Found page heading is no longer GitHub-specific.
- Interview prep adds `pack.profile.interview_questions` and `trial_shift_checklist`; the application's track decides the pack.
- Safety rules add placement fee, visa fee, uniform/medical fee, and agency license signals to the L1 rules.
- Salary advice carries posting period and pay includes with a rationale line.
- Tests cover pack advice, interview, fee flags, and checklist.

## Limits

- Physical/health questions remain `unknown_required` at apply time.
- Interview prep is still deterministic; no live model interview simulation.

## Verification

- `pnpm run ci:quality` passed (591 API tests, 3 skipped; web 18; extension 9; ui 21; evals-lite 103).
- `tests/test_industries_remaining.py` covers detection, search plan, custom pack draft/accept, advice, gaps, interview, safety fees, resume order, and prompt briefs.
- Registry/i18n tests cover every extra pack label, family, and credential.
