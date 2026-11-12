# ka-ux-review

Run a clarity review of $ARGUMENTS (a route path such as `/tracks`, or `diff` for the current git diff).

1. Read `.agent/skills/ux-clarity-review/SKILL.md`, `docs/design/glossary.md`, and `docs/workflow/planned/ux-clarity-overhaul.md` §3, §6, §7.
2. Run `pnpm run check:ux-jargon` and keep the hits for this route.
3. If the local app is running at `http://localhost:3100`, capture the route at 375 / 820 / 1440 in light and dark into `.audit-screenshots/reviews/` (gitignored). Use the Playwright MCP tools or `pnpm run capture:design-screenshots`.
4. Answer the five questions per section from the screenshot alone, then check defaults, templates, the AI draft path, the non-AI fallback, and the empty/loading/error/permission states.
5. Report: section verdicts, at most six issues with Before / After / Why, and the one fix that matters most. Include the responsive gate result at 375.
6. Do not edit application code in this command.

If `$ARGUMENTS` is empty, review the current git diff against `main`.
