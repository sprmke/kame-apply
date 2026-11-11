# Route: `/jobs`

**Page:** `apps/web/app/pages/jobs.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Board list | Done | query | Documented | Phase 6 |
| Drawer / fit | Done | — | Documented | Phase 6 |
| Triage | Done | enum | Documented | Phase 6 |
| Risk seal | Done | — | Documented | Phase 7 |
| Tailor | Done | — | Documented | Phase 9 → `/tailor/:id` |
| Mark applied | Done | — | Documented | Phase 11 → application row |

## Overview

Job research board: ranked matches, readable posting, fit requirements with evidence, keyboard triage. On mobile the list is a full page; selecting a job opens a full-screen document with a back action and a sticky Shortlist / Tailor / Open / Skip bar. Risk seals and reason quotes from Phase 7. Tailor opens the per-job workbench. **Mark applied** creates (or updates) an application and opens its dossier. Optional `?track=` scopes to one search.

## User-facing knowledge

Sort by match (default), newest, or salary. Skip reasons train ranking for that search. Zero results show relaxation suggestions when a search is selected. The header keeps only **Show all** and sort; CSV and the shortcut legend moved out of the primary controls.

## Keyboard

`j`/`k` move, `s` shortlist, `x` skip, `t` tailor, `o` open original, `?` help.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/jobs` | List |
| `GET /api/v1/track-jobs/{id}` | Detail |
| `POST /api/v1/track-jobs/{id}/triage` | Shortlist / skip / … |
| `GET /api/v1/jobs/export.csv` | Export |
| `GET /api/v1/tracks/{id}/relaxations` | Suggestions |
| `POST /api/v1/applications/mark-applied` | Log applied + open dossier |

## RBAC

`data.read` for list/detail/export; `data.write` for triage.

## Implementation map

`apps/web/app/pages/jobs.vue` · `apps/api/app/matching/`
