# Route: `/applications`

**Page:** `apps/web/app/pages/applications.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Table + board | — | filters | Documented | Phase 11 |
| Manual log | — | required fields | Documented | |
| Funnel / outcomes | — | period | Documented | |
| Export CSV | — | — | Documented | |
| Saved views | — | name | Documented | |

## Overview

Applications across searches: table or kanban board, filters, funnel strip, log from scratch, export. The filter is labeled Search. The empty state links to Browse jobs. Status changes from the table select or by dragging on the board. Backward moves ask for a note.

## User-facing knowledge

Log an application when you applied outside the app. Drag cards on the board to update status. Export downloads CSV for the current workspace.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/applications` | List |
| `POST /api/v1/applications/manual` | Create |
| `PATCH /api/v1/applications/{id}/status` | Status |
| `GET /api/v1/applications/export` | CSV/JSON |
| `GET/POST /api/v1/application-views` | Saved views |
| `GET /api/v1/metrics` | Funnel / outcomes |

## RBAC

`data.read` for list/export/metrics; `data.write` for create/status/views.

## Implementation map

`apps/web/app/pages/applications.vue` · `apps/api/app/applications/{tracker,metrics,status}.py`
