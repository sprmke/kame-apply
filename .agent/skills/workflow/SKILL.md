---
name: workflow
description: Manage the docs/workflow lifecycle (intake, planned, in-progress, done, wont-do). Use when starting, finishing, or cancelling a planned piece of work. Filenames are kebab-case slugs with no date prefix.
---

# Workflow lifecycle

| Folder | Meaning |
| --- | --- |
| `docs/workflow/intake/` | Raw ideas and design scratchpads (`<slug>-design.md`) |
| `docs/workflow/planned/` | Approved plans (`<slug>.md`), indexed in `README.md` |
| `docs/workflow/in-progress/` | Current execution; one scratchpad per phase (`phase-NN-<slug>.md`, from `_scratchpad-template.md`) |
| `docs/workflow/done/` | Shipped |
| `docs/workflow/wont-do/` | Declined, with a one-line reason |

Commands: `/workflow-start <slug>`, `/workflow-done`, `/workflow-wont-do`. They call `scripts/dev/workflow-move.sh <start|done|wont-do> <slug>`.

## Rules

- Never move files by hand; use the script, then update the `README.md` index tables in the affected folders in the same session.
- No date prefixes on new workflow docs.
- Finishing a phase also means: tick the phase file's exit criteria and update the status table in `docs/phases/README.md`.

Related: `.cursor/rules/workflow-docs.mdc`, `.cursor/rules/plan-mode.mdc`.
