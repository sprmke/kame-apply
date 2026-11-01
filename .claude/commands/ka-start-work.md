# ka-start-work

Start work on `$ARGUMENTS` (a phase like `phase-03`, or a GitHub issue number).

For a phase:

1. Read `docs/phases/README.md` (confirm dependencies are done), then `docs/phases/phase-NN-*.md` and only the docs it links. Use `/clear` between unrelated goals.
2. Create `docs/workflow/in-progress/phase-NN-<slug>.md` from `_scratchpad-template.md`: vertical slices, open questions, decisions. Add a row to `docs/workflow/in-progress/README.md`.
3. Branch: `git fetch origin && git checkout main && git pull origin main && git checkout -b phase/NN-<slug>`.
4. Per slice: test first where practical → implement → targeted tests → UI check via Playwright MCP at 375/820/1440 → docs updated in the same change. AI features: add or extend eval cases.

For an issue: branch `issue-$ARGUMENTS-short-slug` and read the issue plus the matching phase file.
