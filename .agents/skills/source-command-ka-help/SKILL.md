---
name: "source-command-ka-help"
description: "Migrated source command `ka-help`"
---

# source-command-ka-help

Use this skill when the user asks to run the migrated source command `ka-help`.

## Command Template

# ka-help

Show **Kame Apply commands** (`/ka-*`).

| Command | Use when… |
| --- | --- |
| **/ka-help** | This list |
| **/ka-start-work** `phase-NN` | Begin a phase: read docs, scratchpad, branch |
| **/ka-start-app** | Run the local stack |
| **/ka-check-before-pr** | `pnpm run ci:quality` + verifier/auditor/design-review as applicable |
| **/ka-design-review** | Anti-slop review of a route/diff |
| **/ka-submit-for-review** | Push + open PR with exit-criteria checklist |
| **/ka-pull-new-changes** | Pull latest `main` |
| **/ka-create-new-ticket** | File a GitHub issue |

Also: `/self-review`, `/workflow-start`, `/workflow-done`, `/workflow-wont-do`, `/superpowers-*` (opt-in only).

Docs: `docs/phases/README.md` (build plan), `docs/research/06-agentic-workflow.md` (build loop). Prod unlock: **applywave**.
