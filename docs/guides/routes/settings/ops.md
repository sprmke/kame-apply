# Route: `/settings/ops`

**Page:** `apps/web/app/pages/settings/ops.vue` · **Layout:** `default` · **Access:** admin/owner (`activity.read`)

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Dashboard | pytest ops | RBAC | Done | Phase 14 |

## Overview

Admin view of source health, recent discovery runs, and AI cost for the active workspace.

## Save paths

Read-only. `GET /api/v1/ops/dashboard`.

## Implementation map

`pages/settings/ops.vue`; `apps/api/app/ops/router.py`.
