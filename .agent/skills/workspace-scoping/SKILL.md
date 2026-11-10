---
name: workspace-scoping
description: "Multi-tenancy rules: workspace_id on every tenant row, RLS policies, WorkspaceContext, cross-tenant tests. Use for any new table, query, or endpoint."
---

# Workspace scoping

1. Every tenant-owned table has `workspace_id NOT NULL` with an RLS policy on `current_setting('app.workspace_id')`. The shared job corpus is the only non-tenant data and is read-only to the app role.
2. `WorkspaceContext` resolves `X-Workspace-Id`, checks active membership and role, then runs `SET LOCAL app.workspace_id` and `app.user_id` in the request transaction. Never trust a `workspace_id` in a body or query string.
3. Background work (DBOS steps, MCP tools, extension calls) must set the same context before touching tenant tables. A step without a workspace context fails closed.
4. Tests for every new tenant table: a raw SQL read with the wrong `app.workspace_id` returns 0 rows; a cross-tenant API call returns 404 (not 403, to avoid existence leaks).
5. Blobs in R2 use keys prefixed `ws/<workspace_id>/`; signed URLs are short-lived and issued only after the scope check.
6. Migrations use the template RLS helper and `FORCE ROW LEVEL SECURITY`; the app role has no `BYPASSRLS`.

See `docs/architecture/overview.md` invariant 2 and `.cursor/rules/workspace-scoping.mdc`.
