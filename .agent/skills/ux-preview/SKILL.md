---
name: ux-preview
description: >-
  Build a redesigned page as a dev-only preview route with sample data and real
  Signal components, screenshot it before and after at 375/820/1440, and get
  approval before wiring the API. Use via /ka-ux-preview or when a layout change
  is too big to risk straight on the real route.
---

# UX preview

A preview exists so a layout decision costs one screenshot, not a migration. It ships **nothing**: the route is dev-only, uses fixtures, and is deleted when the real page takes the layout.

## When to use

- A page's structure changes (tabs, panes, stepper, new shell), not just its copy.
- The change touches responsive behaviour at 375 or 820.
- The user asked to see it before it goes live.

Do not use a preview for a string fix, a token change, or a small reorder. Edit the real page.

## Loop

1. **Baseline.** Capture the real route before touching it:
   `pnpm run capture:design-screenshots` or Playwright MCP at 375/820/1440, light and dark. Save to `.audit-screenshots/previews/<slug>/before-<width>.png`.
2. **Build.** Create `apps/web/app/pages/_preview/<slug>.vue`:
   - `definePageMeta({ layout: false })`
   - Guard it exactly like `_design.vue`: `if (!import.meta.dev && !cfg.enableDesign) throw createError({ statusCode: 404 })`.
   - Use fixtures in the file. No API calls, no auth, no writes.
   - Use real `@kame/ui` components and tokens. No new CSS system.
   - Cover empty, loading, error, and mobile states with a small state switcher.
3. **Capture after.** Same three widths, both themes. Save next to the before shots.
4. **Compare and decide.** Screenshot pair per width. Note the decision in `README.md` next to the shots: what changed, why, what was rejected.
5. **Approval gate.** Show the user the pair for 375 and 1440 plus the decision line. Do not implement on the real route before approval.
6. **Implement and delete.** Move the approved layout to the real route in one slice, with API wiring and tests. Delete `_preview/<slug>.vue` and its fixtures in the same PR. Keep only the approved after-shots.

## Rules

- Never link to a preview from product navigation.
- Never call the API from a preview.
- Never leave a preview route in a release build: the `enableDesign` guard is mandatory.
- Fixtures use synthetic people and companies. No real resumes, no sensitive values.
- A preview that needs more than roughly 200 lines of fixture data is a sign the real page should be built with a mock server instead; say so.
- Screenshots: raw captures stay in `.audit-screenshots/` (gitignored). Only the approved after-shots and `README.md` are committed under `docs/design/previews/<slug>/`.

## Output

```
.audit-screenshots/previews/<slug>/before-375.png ... after-1440.png
docs/design/previews/<slug>/README.md      (decision, after shots only)
apps/web/app/pages/_preview/<slug>.vue     (deleted before merge)
```

Report: the decision, the two screenshot paths, and the one thing that still needs the user's taste.
