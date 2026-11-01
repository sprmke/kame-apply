# Route: `/tracks/:id/settings`

**Page:** `apps/web/app/pages/tracks/[id]/settings.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Autonomy | Done | enum | Documented | Live |
| Sources | Done | toggles | Documented | Phase 5 |
| Schedule | Done | preset/tz/quiet/cap | Documented | Phase 10 |
| Pause / resume | Done | status | Documented | Phase 10 |
| Resume Studio | Done | link | Documented | Opens `/studio?track=` |

## Overview

Track settings: autonomy, source toggles, schedules (preset, timezone, quiet hours, daily cap), pause/resume, Studio link.

## User-facing knowledge

Autonomy: Discover → Prepare → Assist → Auto-submit. Schedules run discovery (and prepare when autonomy allows). Pause stops schedules; Resume recalculates the next run. Run history is under Runs.

When autonomy is Auto-submit: dry-run budget, score threshold, kill switch, and dry-run report list (Phase 19). Live enable requires dry-runs exhausted and `AUTO_SUBMIT_ENABLED`.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}` | Load |
| `PATCH /api/v1/tracks/{id}` | Autonomy / metadata |
| `GET /api/v1/tracks/{id}/sources` | List track sources |
| `PATCH /api/v1/tracks/{id}/sources/{source_id}` | Enable/params |
| `GET/POST /api/v1/tracks/{id}/schedules` | List / create schedule |
| `DELETE /api/v1/schedules/{id}` | Delete schedule |
| `POST /api/v1/tracks/{id}/pause\|resume` | Pause / resume |

## Implementation map

`tracks/[id]/settings.vue`, `apps/api/app/schedules/`. See `docs/architecture/automation.md`.
