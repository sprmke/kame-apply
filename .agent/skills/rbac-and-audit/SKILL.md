---
name: rbac-and-audit
description: "RBAC and audit decision habit for every new capability: workspace roles (owner/admin/member/viewer) plus activity_log."
---

# RBAC and audit

For every new capability:

1. **RBAC**: which of `owner | admin | member | viewer` can view or mutate? Enforce with `require_role` on the endpoint (and the MCP tool, which calls the same service); gate the UI the same way but never rely on it.
2. **Tenancy**: the row carries `workspace_id` and is covered by an RLS policy (`workspace-scoping`).
3. **Audit**: mutations emit an `activity_log` event, or the change notes `activity-log: N/A — <why>` (`audit-logging`).

The action × role matrix lives in `docs/phases/phase-02-auth-tenancy-shell.md`; update it when you add an action.
