# Applications tracker & command center

Phase 11. Related: `docs/phases/phase-11-tracker-and-command-center.md`, Home (`GET /home`), metrics (`GET /metrics`).

## Status machine

Statuses: `draft`, `ready`, `in_progress`, `needs_you`, `submitted`, `responded`, `interview`, `offer`, `rejected`, `withdrawn`, `ghosted`, `job_closed`.

Legacy `applied` normalizes to `submitted`. Regressions (for example interview → rejected) require a note. Ghosted is suggested after N days without response; the user confirms.

## Tables

| Table | Role |
| --- | --- |
| `applications` | One row per Track+job apply; denormalized company/title; reminder + follow-up draft; optional R2 job snapshot key |
| `application_events` | Append-only timeline |
| `application_reminders` | Follow-up and similar; draft text only (never auto-sent) |
| `application_metrics_daily` | Optional materialized daily aggregates |
| `application_saved_views` | Per-user filter presets |

RLS on `app.workspace_id` for all of the above.

## Snapshots

On submit / mark-applied (when storage is available), sanitized job JSON goes to R2 at `ws/<workspace_id>/applications/<app_id>/job-snapshot.json`. Detail falls back to live job text if no snapshot yet.

## API

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/applications` | Filters: track, status, method, q, submitted date range; pagination |
| GET | `/applications/export` | `fmt=csv\|json` |
| POST | `/applications/mark-applied` | From `track_job_id` or job+track; duplicate warning |
| POST | `/applications/manual` | Company + title + URL; creates stub job |
| GET/PATCH | `/applications/{id}` | Detail; status / notes |
| GET/POST | `/application-views` | Saved filters |
| GET | `/metrics` | KPIs, funnel, outcome breakdowns |
| GET | `/home` | Needs-you, KPIs, Track cards, reminders, activity |

## Outcomes

`GET /metrics` returns response/interview rates overall and by method / tailored-vs-base for ranking and Lens calibration feedback ("what's working").

## Mutations → audit

`application.marked_applied`, `application.created_manual`, `application.status_changed`, `application.notes_updated`, `application.saved_view`.
