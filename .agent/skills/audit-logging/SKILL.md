---
name: audit-logging
description: Append-only activity_log: when to emit, event naming, what never to store. Use for any mutation.
---

# Audit logging

Every state-changing action writes an append-only `activity_log` row: workspace, actor (user, agent, system), `action` (`resource.verb`, e.g. `application.status_changed`), target type and id, before/after summary, request id, timestamp.

- Emit from the **service** function, in the same transaction as the write, not from the router.
- Cover: user mutations, workflow-driven changes, AI drafts accepted/rejected, checkpoint decisions, MCP/agent writes (actor = the agent client).
- Never store secrets, tokens, raw resume text, answers to sensitive fields, or full job descriptions. Store ids and short diffs.
- No update or delete path exists for `activity_log`; retention is a separate job.
- If a change genuinely needs no event, write `activity-log: N/A — <why>` in the PR/scratchpad.
- Add new event names to the catalog in `docs/architecture/data-model.md` (or the module's doc) in the same change.
