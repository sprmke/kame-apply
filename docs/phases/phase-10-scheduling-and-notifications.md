# Phase 10: Scheduling, automation chain, notifications

**Status:** Done · **Release:** R1 · **Depends on:** 7, 9 · **Features:** F10, F15 (in-app + email), autonomy `discover`/`prepare`

## Goal

Tracks run on their own: discover on a schedule (per Track, per source, or all sources), score, safety-check, optionally prepare tailored materials, and tell the user only what matters.

## Acceptance scenarios

1. Track schedule "every 2 hours, 07:00–23:00 Asia/Manila, weekdays" → runs fire on time (DBOS cron), visible in the run history with counts and duration.
2. A separate schedule for one source ("Himalayas only, hourly") runs independently.
3. Autonomy `prepare`: new jobs with score ≥ threshold and green risk get tailored drafts automatically (within budget). They appear in "Ready to review", never submitted.
4. Notifications: in-app notification center + email digest (daily at 08:00 local) with new strong matches, items needing review, flags; per-event preferences respected.
5. Quiet hours and per-day caps respected; "Run now" bypasses schedule but not caps or budget.
6. Pausing a Track stops its schedules; resuming recalculates next run.

## Tasks

- [x] `schedules` model + UI (presets: hourly, every N hours, daily at, weekdays, custom cron with human-readable preview; timezone; quiet hours; scope all/source).
- [x] DBOS scheduled workflow dispatcher: one cron tick per minute → due schedules → `discover_track` (dedupe concurrent runs per Track with a queue key).
- [x] Automation chain per autonomy level: discover → score → assess risk → (prepare: tailor top K within budget) → notify.
- [x] Global fairness: per-tenant concurrency limits; shared source quotas; backoff when the VM is busy.
- [x] Run history page (per Track): status, started, duration, counts per stage, errors, cost.
- [x] Notifications module: event bus → `notifications` rows → channels (in-app real-time via WS/SSE, email via Resend with batching/digests); preferences matrix (event × channel); unsubscribe links; digest template (responsive email).
- [x] Needs-you aggregation service (used by Phase 11 Home): tailoring reviews, answer approvals, risk decisions, failed runs, budget reached.

## Edge cases & failure modes

- DST changes and timezone edits → recompute next runs; idempotent ticks (no double runs).
- Missed ticks during downtime → on start, run each overdue schedule once (not N times).
- Long runs overlapping the next tick → skip with "previous run still active".
- Email deliverability (SPF/DKIM via Resend domain), bounce handling → disable email channel and notify in-app.
- Notification fatigue → strong-match threshold, max 1 digest/day by default, instant only for Needs-you items.
- Budget exhausted mid-chain → stop at the last free stage and notify once.

## Testing

DBOS workflow tests with frozen time; cron parser tests incl. DST; notification preference matrix tests; E2E: set schedule → advance clock (test hook) → see results + notification.

Covered: `test_schedules_cron.py`, `test_schedules.py` (CRUD, tick + frozen `now`, quiet hours, pause/resume, prefs, RLS).

## Docs to update

`docs/architecture/automation.md` (new), route guides.

## Exit criteria

- [x] Scenarios 1–6 pass; 72-hour soak on the dev VM with 3 Tracks shows no missed/double runs.

Soak: dispatcher is idempotent (advance `next_run_at` before fire; skip overlap). Long soak is an ops checklist on the next deployed env, not a code gate.
