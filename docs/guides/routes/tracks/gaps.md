# Route: `/tracks/:id/gaps`

**Page:** `apps/web/app/pages/tracks/[id]/gaps.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Suggest | — | track must-skills | Documented | Phase 20d |
| Status | — | open/in_progress/done/skipped | Documented | |

## Overview

Gap plan for skills the Track requires that are missing from the linked Career Profile. Suggest creates items; status tracks progress.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}/gap-plan` | List |
| `POST /api/v1/tracks/{id}/gap-plan/refresh` | Suggest missing must-skills |
| `PATCH /api/v1/gap-plan/{id}` | Update status |

## RBAC

`data.read` / `data.write`. Cross-tenant track id → 404.
