# Route: `/tracks/:id/runs`

**Page:** `apps/web/app/pages/tracks/[id]/runs.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| History list | Manual | — | Done | Phase 10 |

## Overview

Per-search discovery history. Status, trigger, and duration use plain labels (Completed, Running, Queued, Failed; Run now, Scheduled). The empty state links back to Run search.

## API reference

| Call | Purpose |
| --- | --- |
| GET `/api/v1/tracks/{id}/runs` | History |

## Implementation map

`apps/web/app/pages/tracks/[id]/runs.vue`, `apps/api/app/schedules/service.py` `list_run_history`.
