# ka-ux-preview

Build a dev-only preview of the redesigned $ARGUMENTS route, then show before and after screenshots.

1. Read `.agent/skills/ux-preview/SKILL.md` and the current route guide for the page.
2. Capture the real route before any change at 375 / 820 / 1440 (light and dark) into `.audit-screenshots/previews/<slug>/before-*.png`.
3. Build `apps/web/app/pages/_preview/<slug>.vue` with fixtures, real `@kame/ui` components, and the `enableDesign` guard. No API calls, no writes, no new CSS system.
4. Capture after shots at the same widths. Compare, then write `docs/design/previews/<slug>/README.md` with the decision and the rejected alternative.
5. Stop and ask for approval. Do not touch the real route until it is given. After approval, implement, test, delete the preview, and update the route guide.

If `$ARGUMENTS` is empty, ask which route to preview.
