# Automation: schedules, chain, notifications

Phase 10. Related: `docs/architecture/overview.md` §3 workflows, `docs/phases/phase-10-scheduling-and-notifications.md`.

## Schedules

Table `schedules`: per-Track cron (5-field), timezone, quiet hours `{start,end}` local, `daily_cap`, scope `all|source`, `next_run_at`.

Presets: `hourly`, `every_2_hours`, `every_4_hours`, `daily_morning`, `weekdays_2h`, `custom`.

Pausing a Track (`POST /tracks/{id}/pause`) disables its schedules; resume recalculates `next_run_at`.

## Dispatcher

`POST /api/v1/schedules/tick` (workspace-scoped by default; optional frozen `now` for tests) loads due rows (`enabled` and `next_run_at <= now`) and fires each **once**:

1. Skip if Track not `active`, quiet hours, daily cap, previous run still active, or workspace concurrency ≥ 2.
2. Advance `next_run_at` before work (idempotent; missed ticks do not stack).
3. Run the automation chain.

Deployed environments run an in-process minute loop (`app/schedules/scheduler.py`, `SCHEDULER_ENABLED`). It lists live workspaces through the `scheduler_workspace_ids()` security-definer helper (tenant RLS hides `workspaces` from a context-less transaction), then ticks each workspace with its own RLS context. `POST /schedules/tick` is always scoped to the caller's workspace and remains the test/manual hook. A duplicate tick is a no-op because `next_run_at` advances before work.

## Automation chain

`discover → score → assess risk → (prepare: tailor top K) → notify`

- Autonomy `discover`: stop after score + risk notify.
- Autonomy `prepare` / `assist` / `auto_submit`: also tailor green + score ≥ threshold drafts. **Never submits.**
- Budget exhaustion mid-prepare: stop and emit `budget_reached` once.
- Strong matches: in-app (email via digest only). Needs-you class events may email instantly per prefs.

## Caps and fairness

- Per-schedule `daily_cap` (default 12). **Run now** bypasses cron timing but not the cap.
- Per-workspace concurrent discovery runs: 2.
- Overlapping tick while a Track run is active → skip `previous_run_still_active`.

## Notifications

- `notifications` rows are per-user; dedupe `(workspace_id, user_id, type, dedupe_key)`.
- Prefs matrix: event × channel (`in_app`, `email`). Defaults: in-app all on; email on for needs-you + digest.
- Digest: once per local day near 08:00; max one digest/day.
- Unsubscribe email disables the email channel for the workspace member.
- SSE `/notifications/stream` returns a snapshot; clients poll unread count / list.

## Needs you

`GET /api/v1/needs-you` aggregates tailor reviews, risk decisions without override, failed runs, unread budget alerts. Phase 11 Home consumes the same service.

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/tracks/{id}/schedules` | List / create |
| PATCH/DELETE | `/schedules/{id}` | Update / delete |
| POST | `/tracks/{id}/pause\|resume` | Pause / resume Track |
| GET | `/tracks/{id}/runs` | Run history |
| POST | `/schedules/tick` | Dispatcher (test hook: `now`) |
| GET | `/notifications`, `/needs-you` | Inbox + aggregation |
| GET/PUT | `/notification-prefs` | Preference matrix |
