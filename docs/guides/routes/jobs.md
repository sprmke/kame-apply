# Route: `/jobs`

**Page:** `apps/web/app/pages/jobs.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Board list | Done | query | Documented | Score column, one-line titles |
| Drawer / fit | Done | — | Documented | Phase 6 |
| Triage | Done | enum | Documented | Phase 6 |
| Risk seal | Done | — | Documented | Phase 7 |
| Tailor | Done | — | Documented | Phase 9 → `/tailor/:id` |
| Mark applied | Done | — | Documented | Phase 11 → application row |

## Overview

Job research board: ranked matches, a formatted and collapsible posting, fit requirements with evidence, keyboard triage. The list is a three-column reader: match score, title, company and work mode. The posting is parsed into headings, paragraphs, lists, and tool chips by `JobDescription`; the first two sections show by default and **Read full description** reveals the rest. On mobile the list is a full page; selecting a job opens a full-screen document with a back action and a sticky Shortlist / Tailor / Open / Skip bar. Risk seals and reason quotes from Phase 7. Tailor opens the per-job workbench. **Mark applied** creates (or updates) an application and opens its dossier. Optional `?track=` scopes to one search.

## User-facing knowledge

The list column has a `Match` / `Job` header so the leading number is self-explanatory. Every row is the same height: the score is right-aligned in a fixed 2.25rem column, the title is clamped to one line with the full text on hover, and company and work mode share a second line. Risk appears inline as `! Caution` or `✕ High risk`, and an ineligible job is marked in the same line, so no row carries chips or wrapping text. Sort by match (default), newest, or salary. Skip reasons train ranking for that search. Zero results show relaxation suggestions when a search is selected. The header keeps only **Include ineligible** and sort; CSV and the shortcut legend moved out of the primary controls. The right panel leads with the score and risk seal, then **Next**: **Tailor** is the one filled action, **Shortlist** and **Open** sit under it, and **Skip** and **Mark applied** close the block as text actions. Risk reasons show only on caution and high-risk jobs, so a clear seal never carries a warning quote. Fit checks come after the actions and are clamped to three lines with a **Show all checks** control.

## Sections

### Board list

- Header: `Match` over the score column, `Job` over the text column.
- Row: right-aligned tabular score, then a two-line text block. Title truncates on one line (`title` attribute carries the full text); the second line is company, work mode, and any status marker.
- Selected row: `bg-brand-50` with a 2px brand inset on the left edge; the score turns brand-700.
- Reason chips live in the right panel, not in the list, so repeated signals such as "Title match" do not repeat down the column.
- The column is `min-w-0` at every breakpoint: verify no horizontal scroll at 375px.

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

`apps/web/app/pages/jobs.vue`, `apps/web/app/components/JobDescription.vue`, `apps/web/app/lib/job-description.ts` · `apps/api/app/matching/`
