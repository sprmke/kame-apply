---
name: dbos-workflows
description: DBOS Transact workflow/step design, idempotency, recv/send checkpoints, schedules, queues, and testing. Use when adding or changing a durable workflow.
---

# DBOS workflows

Catalog: `docs/architecture/overview.md` §3. Rule: `.cursor/rules/dbos-workflows.mdc`. Check current APIs with `context7` or by inspecting the installed package (DBOS Python moves fast; the spike note lists known API changes).

- **Workflow = orchestration only**, deterministic; **step = one side effect**, idempotent, small result. Anything calling the network, DB writes, LLMs, or the clock lives in a step.
- **Idempotency**: derive keys from business ids (`job_id`, `run_id`, `step_no`); external effects check-then-act inside the step.
- **Human checkpoints**: workflow `DBOS.recv("decision", timeout)`; API endpoint calls `DBOS.send` after persisting the decision. Timeouts move the run to `needs_you`, never fail it.
- **Queues**: register after launch with `DBOS.register_queue(name, global_concurrency=, partition_concurrency=, limiter=)`; per-host politeness = `queue_partition_key=host` + `partition_concurrency=1` (+ `partition_limiter`). `Queue(...)` cannot be constructed directly.
- **Schedules**: `@DBOS.scheduled` no longer exists. Use `DBOS.create_schedule(schedule_name=, workflow_fn=, schedule=<cron>)` per Track and pause/resume/delete it when the Track changes. Spike: `docs/architecture/spikes/01-dbos.md`.
- **Tenancy**: set the workspace context at the top of each tenant-touching step.
- **Payloads**: JSON-serializable, small; blobs go to R2 by key.
- **Tests**: run workflows against the local Postgres; kill and relaunch mid-run to assert resume from the last completed step; assert no duplicate side effects.
