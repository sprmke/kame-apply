# IND-2: Picker and visibility (scratchpad)

**Branch:** `ind/01-pack-foundation` (shared worktree) · **Started:** 2026-11-13 · **Plan:** `docs/workflow/done/multi-industry-support.md`

## Shipped

- `useExperience()` loads `GET /workspace/experience` and exposes pack states, labels, facets, and features.
- Create workspace is now two steps: name, then field of work. Chosen fields are written through the workspace API; the default Technology field is removed when only another field is chosen.
- `IndustryPicker` (shared card picker) with primary marker and a two-field limit.
- Settings > General > **Fields of work**: add, remove, make primary, and an inline consequence preview before a primary change.
- New search: field chips from enabled packs, templates filtered by field, `industry` sent on create, field label on each search row.
- Criteria page: pack-driven states. Visible fields inline, collapsed under **More filters**, hidden behind **Show all filters** with a **Set earlier** line. New controls: shifts, employment types, pay includes, facets, relocation, posting age.
- `check:industry-branches` script in `ci:quality`; no `industry ===` in `apps/web/app`.
- UI checked at 375, 820, 1440 with a real Hospitality workspace and track. Facet save and reload verified.

## Verification

- `pnpm run ci:quality` passed (570 API tests, 3 skipped; web 18; extension 9; ui 21; evals-lite 103).
- `pnpm run check:industry-branches` passes.
- Manual run at 375, 820, 1440 with a real Hospitality workspace:
  - create workspace step 2 shows General, Technology, Hospitality;
  - Hospitality removes Technology from the workspace, so the new search sees only Hospitality + General;
  - 15 kitchen templates appear and tech templates do not;
  - Sous Chef track shows kitchen facets, shifts, pay includes, and hides timezone/education;
  - selecting Filipino, Hotel, Grill, Evening and saving persists after reload;
  - Show all filters reveals hidden fields and the Set earlier line;
  - Settings > Fields of work add, make primary preview, and remove work.
- Screenshots were reviewed and removed; not committed.

## Follow-ups

- Profile, Answers, Resume, and Jobs ledger rows still need their pack wiring (IND-6 to IND-8).
- Dark-mode screenshots and a `design-reviewer` pass remain for the PR review step.
