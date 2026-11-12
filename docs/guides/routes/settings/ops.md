# Route: `/settings/ops`

**Page:** `apps/web/app/pages/settings/ops.vue` · **Layout:** `default` · **Access:** admin/owner (`activity.read`)

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| AI cost | pytest ops | RBAC | Done | Spent and budget, per feature |
| Sources | pytest ops | RBAC | Done | Same health fields as Source health |
| Recent runs | pytest ops | RBAC | Done | Status, trigger, time |

## Overview

Admin view of AI cost, source health, and recent discovery runs for the active workspace. Three section cards. The page is titled **System status** everywhere, matching the nav label.

## User-facing knowledge

This page is for owners and admins. It shows what the workspace spent on AI this month, whether each source is answering, and what ran recently.

## Save paths

Read-only. `GET /api/v1/ops/dashboard`.

## States

Loading: skeleton. Error: a single line to retry. Empty lists: one line each ("No AI calls this month.", "No sources yet.", "No runs this week").

## Implementation map

`pages/settings/ops.vue`; `apps/api/app/ops/router.py`; `FnSectionCard`.
