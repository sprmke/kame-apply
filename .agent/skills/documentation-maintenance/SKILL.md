---
name: documentation-maintenance
description: >-
  Update project docs in the same change as code. REQUIRED whenever implementing
  or materially changing features, routes, pages, UI behavior, API endpoints,
  migrations, env vars, integrations, AI features, or user-visible flows. Use
  before claiming a task done or finishing a phase. Mirrors the always-on Cursor
  rule documentation-maintenance.mdc (Claude Code cannot auto-load .mdc files).
---

# Documentation maintenance (same-change docs)

## When this applies (almost always)

New or changed features, routes, pages, validation, save paths, permissions, UX, API shapes, env vars, DB schema or migrations, integrations, AI features and prompts, workflows and checkpoints.

**Skip only:** typos, formatting-only, internal renames with no API/UX impact.

## What to update

| Change | Update |
| --- | --- |
| Architecture, API surface, data model, env vars, deployment | `docs/architecture/*.md` |
| Page / section behavior, save flows, validation | `docs/guides/routes/*`, via the **`route-guides`** skill |
| Product scope | `docs/prd.md` |
| Stack change | `docs/tech-stack.md` |
| Workflow, checkpoint, or apply-engine behavior | `docs/architecture/overview.md` §3 and the owning phase file |
| Mutating capability | **`audit-logging`**: emit an `activity_log` event or write `activity-log: N/A — <why>` |
| Migration or backfill | `docs/architecture/deployment.md` |
| Design tokens / components | `docs/design/design-system.md` (and `DESIGN.md` once Phase 2 distills it) |
| Phase progress | phase file checklist + `docs/phases/README.md` status table |
| Rules agents rely on | `CLAUDE.md` and the matching `.cursor/rules/*.mdc` |

Canonical detail: `.cursor/rules/documentation-maintenance.mdc`; route mapping: `.cursor/rules/route-guides.mdc`; always-loaded copy: `CLAUDE.md` § Docs are the source of truth.

## Workflow

1. Identify which rows above apply.
2. Implement the change.
3. Update docs in the same session; small accurate edits, never deferred.
4. Route/page work: run the `route-guides` checklist.
5. Before saying done, confirm docs were touched or note why the change is docs-exempt.

## Finish checklist

- [ ] Route guide updated if any page/section/UX changed
- [ ] `docs/architecture/*` updated if API / env / architecture / data model changed
- [ ] `.cursor/rules/*.mdc` updated if an invariant changed
- [ ] `activity_log` event emitted, or explicit `activity-log: N/A — <why>`
- [ ] Phase checklist and status table updated if a phase task completed
