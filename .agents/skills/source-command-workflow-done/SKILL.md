---
name: "source-command-workflow-done"
description: "Migrated source command `workflow-done`"
---

# source-command-workflow-done

Use this skill when the user asks to run the migrated source command `workflow-done`.

## Command Template

# Workflow done

Mark the active **in-progress** workflow doc as **done**.

## Steps

1. Identify the in-progress slug from `docs/workflow/in-progress/` or user message.
2. Run:

```bash
bash scripts/dev/workflow-move.sh done <slug>
```

3. Confirm docs/route guides/architecture updates were made — invoke **`documentation-maintenance`** (+ **`route-guides`** if pages changed). See `.cursor/rules/documentation-maintenance.mdc` and `AGENTS.md` § Docs are the source of truth.
4. Update the index tables in `docs/workflow/*/README.md` (remove the old row, add the done row with a link), and tick the phase checklist in `docs/phases/`.
