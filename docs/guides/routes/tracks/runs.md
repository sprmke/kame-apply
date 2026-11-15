# Route: `/tracks/:id/runs`

**Page:** `apps/web/app/pages/tracks/[id]/runs.vue` · **Shell:** `apps/web/app/components/TrackShell.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Summary line | Manual | — | Documented | Run count and new matches |
| Run table | Manual | — | Documented | Run, Found, Duration |
| Live indicator | Manual | — | Documented | Polls every 15s; shows a pulse while running |
| Empty state | Manual | — | Documented | Links to Run search |

## Overview

The **History** tab is a log, not a feed. One table, three columns, newest first. Status, trigger, and time share one cell so the row reads as a sentence; counts appear only when they are non-zero, so a quiet run says "Nothing new" instead of "0 new · 0 scored · 0 prepared".

## User-facing knowledge

Each row is one search run. Hover the time to see the exact date. Failed runs show the error under the status. Runs appear here after any run, scheduled or manual.

### Common user questions

- **Why does a run say "Nothing new"?** Nothing passed the filters or everything found was already seen.
- **Can I re-run from here?** Yes. The empty state links back to Criteria, where **Run search** lives.

## Sections

### Summary

`{runs} runs · {found} new matches` for the listed runs, with a pulsing "Running now" marker while any run is queued or running.

### Table

`FnTable` with a recessed header, compact density, and a screen-reader caption.

| Column | Content |
| --- | --- |
| Run | Status dot + word (Completed, Failed, Running, Queued), then trigger and relative time, then the error when present |
| Found | "3 new matches", plus scored/prepared when non-zero; "Nothing new" otherwise |
| Duration | Whole seconds |

Status uses colour, glyph, and word. Relative times use `Intl.RelativeTimeFormat` in the user's locale; the absolute timestamp is in the `title`.

## Loading / errors

The query polls every 15s. The empty state is a dashed card with one action, and only renders once the query has resolved, so it never flashes while loading.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}/runs` | Run history |

## Implementation map

`tracks/[id]/runs.vue`, `apps/api/app/schedules/service.py` `list_run_history`.

## UX clarity (2026-11-12)

- History sits in one section with an intro line and a summary sentence.
- The table stacks into labelled cards under 640px, so run status and new matches are readable on a phone.
- Failed runs add one plain line: try again, then check the sources.
