# Spike 1: DBOS Transact (Python)

**Date:** 2026-10-28 · **Decision: KEEP** · Code: `spikes/dbos_spike.py`, `spikes/run_dbos_spike.sh` · Version tested: `dbos` 3.3.0 on Postgres 17.

## What was proven

| Claim | Result |
| --- | --- |
| Durable wait: step 1 → `DBOS.recv` (step 2) → step 3; `SIGKILL` the process during the wait; restart; `DBOS.send` | Workflow completed from the wait. `step_one` ran **once** across both processes (log count = 1), `step_three` once. |
| Cron schedule | `DBOS.create_schedule(... schedule="* * * * * *")` fired 4 times in 5.5 s. |
| Per-key concurrency 1 | Queue with `partition_concurrency=1` and `queue_partition_key`: max concurrent per key = 1 for keys `a` and `b`. |
| Rate limit | `limiter=QueueRateLimit(limit=3, period=2.0)`: 6 tasks started at offsets `[0, 0, 0, 2.1, 2.1, 2.1]` s. |

## API differences from older docs (update when reading tutorials)

- `@DBOS.scheduled` is **gone**. Schedules are DB-backed: `DBOS.create_schedule(schedule_name=, workflow_fn=, schedule=, context=)` (also `pause_schedule`, `resume_schedule`, `trigger_schedule`, `backfill_schedule`). This suits per-Track schedules: create/update/delete a schedule row when a Track's schedule changes, instead of a polling dispatcher.
- `Queue(...)` cannot be constructed directly. Use `DBOS.register_queue(name, global_concurrency=, partition_concurrency=, limiter=)` **after** `DBOS.launch()`; queues are persisted in the system DB.
- Workflow ids: `with SetWorkflowID("id"): DBOS.start_workflow(fn, ...)`. Partition key: `with SetEnqueueOptions(queue_partition_key="host"): queue.enqueue(fn, ...)`.
- Config key is `system_database_url` (sync `postgresql://` URL), separate from the app's asyncpg URL.
- Queue polling interval defaults to 1 s: keyed tasks that sleep 0.6 s took ~5 s for 6 tasks. Lower `polling_interval_sec` for latency-sensitive queues.

## Consequences

- Keep DBOS; Hatchet fallback not needed. Add `dbos` to `apps/api` dependencies in the first phase that ships a workflow (Phase 5) and pin it.
- Per-host politeness (Phase 5): one queue, `queue_partition_key=host`, `partition_concurrency=1`, plus `partition_limiter` for the host's rate.
- Update the `dbos-workflows` skill/rule (done in this phase).
