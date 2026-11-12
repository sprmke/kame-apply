# Route: `/settings/danger`

**Page:** `apps/web/app/pages/settings/danger.vue` · **Layout:** `default` · **Access:** signed in; actions depend on role

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Export a copy | pytest Phase 14 | owner only | Done | JSON without secrets |
| Transfer ownership | pytest | target must be a member | Done | You become an admin |
| Leave workspace | acceptance.spec.ts (pytest rules) | owner cannot leave | Done |  |
| Delete this workspace | pytest | type the name to confirm | Done | Soft-delete + immediate R2 purge; rows after 30 days |

## Overview

One section card per action, destructive last. The lede says what the page does: export a copy, or transfer, leave, or delete this workspace.

## User-facing knowledge

Personal workspaces cannot be transferred or deleted; the page says so and offers a support address. In a team workspace the owner transfers or deletes; everyone else can leave. Export downloads JSON without secrets or file bytes.

**Common user questions**

- **I am the owner and want to leave.** Transfer ownership to another member first.
- **Can I undo a delete?** Files are removed from object storage immediately. The workspace row is hidden and purged after 30 days. Contact support within that window.

## Actions

Each action has its own card: title, one consequence line, one button. Buttons are verb + object: Download copy, Transfer ownership, Leave workspace, Delete workspace. Every action opens a confirm dialog that repeats the consequence; delete also requires typing the workspace name.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/workspace/export` | Owner JSON export |
| `POST /api/v1/workspace/leave`, `POST .../transfer`, `DELETE /api/v1/workspace` |  |

## Implementation map

`pages/settings/danger.vue`; i18n `danger.*`; `FnSectionCard`.
