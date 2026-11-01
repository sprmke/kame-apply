# ka-design-review

Run an anti-slop design review of $ARGUMENTS (a route path such as `/jobs`, or `diff` for the current git diff).

1. Read `.cursor/rules/anti-slop-design.mdc`, `.agent/skills/design-review/SKILL.md`, and `docs/design/design-system.md`.
2. Run `pnpm run check:design-slop` if it exists.
3. If a route is given and the local app is running, capture screenshots (`pnpm run capture:design-screenshots`) at 375 / 820 / 1440 in light and dark. Output: `.audit-screenshots/harness/` (gitignored).
4. Follow the skill report format. At most six issues. `file:line` on every code finding.
5. The palette and fonts are ratified in the design system; do not propose alternatives.

If `$ARGUMENTS` is empty, review the current git diff against `main`.
