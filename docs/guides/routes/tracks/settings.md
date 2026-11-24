# Route: `/tracks/:id/settings`

**Page:** `apps/web/app/pages/tracks/[id]/settings.vue` · **Shell:** `apps/web/app/components/TrackShell.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Autonomy | Done | enum | Documented | Four-step ladder, saves on change |
| Auto-submit panel | Done | dry runs, threshold | Documented | Only shown for Auto-submit |
| Sources | Done | per-source toggle | Documented | Collapsed summary, grouped when open |
| Schedule | Done | preset/tz/quiet/cap | Documented | On/off per schedule, delete, add form |
| Pause / resume | Done | status | Documented | Stops every schedule for this search |

## Overview

The **Automation** tab answers a different question from Criteria: how this search runs. Three cards only, each a single idea. The tab is named Automation so it no longer shares a word with the page that holds the criteria.

## User-facing knowledge

Autonomy climbs one step at a time. Discover finds and scores; Prepare adds a resume and cover letter; Assist fills forms but you still submit; Auto-submit sends without a final click when every check passes. Pausing stops scheduled runs and keeps everything else.

### Common user questions

- **Is there a Save button?** No. Choosing a rung of the ladder saves it. Schedule and source changes save as you make them.
- **What does turning a source off do?** This search stops checking that board. Other searches are unaffected.
- **Where did the Studio link go?** Resume studio is in the left rail and in More tools on every search page.

## Sections

### Autonomy

A radio ladder of four options with one plain line each, numbered 1 to 4 so the direction is obvious. Changing the radio `PATCH`es the track autonomy and refetches; a failed save rolls the selection back to the previous value and raises an error toast.

### Auto-submit

Rendered under the ladder only when Auto-submit is selected: dry-runs left, score threshold, **Enable live** (disabled until dry runs are exhausted), the kill switch, and the dry-run report list.

### Sources

Collapsed row: "9 of 12 on" plus a **Change** control. Open, sources are grouped into Job boards, Company ATS, and Other, two columns from `sm`. Names are humanised (`smartrecruiters` → SmartRecruiters). Each checkbox `PATCH`es that track source immediately.

### Schedule

Shows the saved schedules, each with the frequency and timezone, quiet hours, daily cap, next run, and last skip reason, plus an On/Off checkbox and Delete. **Add schedule** opens a labelled form (frequency, timezone, quiet start/end, daily cap) instead of leaving the form on the page. The Active/Paused control and **Pause** / **Resume** sit in the section header.

## Loading / errors

`TrackShell` covers the loading and error states for the page chrome. The recommended card, schedule rows, and source list each load in place: a card and list-row skeleton with the same heights, never a spinner. Failed mutations raise a toast and leave the previous value in place.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}` | Load track + autonomy |
| `PATCH /api/v1/tracks/{id}` | Autonomy |
| `GET /api/v1/tracks/{id}/sources` | List track sources |
| `PATCH /api/v1/tracks/{id}/sources/{source_id}` | Enable/disable one source |
| `GET/POST /api/v1/tracks/{id}/schedules` | List / create schedule |
| `PATCH /api/v1/schedules/{id}` | Enable/disable a schedule |
| `DELETE /api/v1/schedules/{id}` | Delete schedule |
| `GET/PUT /api/v1/tracks/{id}/auto-submit` | Auto-submit settings |
| `GET /api/v1/tracks/{id}/auto-submit/dry-runs` | Dry-run report |
| `POST /api/v1/tracks/{id}/pause\|resume` | Pause / resume |

## Implementation map

`tracks/[id]/settings.vue`, `apps/api/app/schedules/`, `apps/api/app/autosubmit/`. See `docs/architecture/automation.md`.

## UX clarity (2026-11-12)

- Three blocks, each one sentence of consequence: **How much we do**, **When we search**, **Where we look**.
- **How much we do** uses radio cards with a **Recommended** badge on Find and prepare and an **Advanced** badge on Apply for me. The summary line states what actually happens.
- Auto-apply shows practice runs as "N of 3 done", **Minimum match** as a whole number, **Turn on auto-apply**, **Pause auto-apply**, and the always-manual platforms (LinkedIn, Indeed, JobStreet).
- Timezone is a select seeded from the device zone. Quiet hours and **New jobs per day** carry `?` help.
- Sources are grouped as **Job sites** and **Company career sites**.


## Recommendation (2026-11-13)

A card at the top of Automation shows **Recommended for this search**: schedule, how much we do, daily cap, and up to three reasons. **Use recommended** applies autonomy and creates or updates the schedule through the audited endpoints. Rules only; no AI call.
