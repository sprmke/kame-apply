---
name: field-notes-components
description: How to build or extend Signal signature components (proof mark, pencil text, fit ledger, route line, risk seal, grade ring, dossier, Needs-you stack, live window, command bar).
---

# Signal components

Spec: `docs/design/design-system.md` §7 and `docs/design/ux-blueprint.md`. Rules: `vue-components.mdc`, `anti-slop-design.mdc`.

1. Check `packages/ui` and the `/_design` route for an existing component before building.
2. Build on Reka UI primitives where behavior exists (popover for proof marks, dialog for sheets, tabs).
3. Variants through `tailwind-variants`; tokens only; light and dark; compact and comfortable density.
4. Meaning needs two channels (color + glyph + word). Proof marks and pencil text are keyboard reachable.
5. Add loading/empty/error variants and a `/_design` story at 375/820/1440 in both themes.
6. Visual regression: Playwright screenshot of the story.
7. Run `/ka-design-review` before merging.
