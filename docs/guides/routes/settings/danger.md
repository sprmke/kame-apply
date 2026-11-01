# Route: `/settings/danger`

**Page:** `apps/web/app/pages/settings/danger.vue` · **Layout:** `default` · **Access:** signed in; actions depend on role

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Leave | acceptance.spec.ts (pytest rules) | owner cannot leave | Done |  |
| Transfer | pytest | target must be a member | Done |  |
| Delete | pytest | type the name to confirm | Done | Soft-delete + immediate R2 purge; rows after 30 days |
| Export | pytest Phase 14 | owner only | Done | JSON without secrets |

## Overview

Leave, transfer, export, or delete a team workspace. Owners can export any workspace (including personal).

## User-facing knowledge

Personal workspaces cannot be left, transferred or deleted. In a team workspace the owner transfers or deletes; everyone else can leave. Export downloads JSON without secrets or file bytes.

**Common user questions**

- **I am the owner and want to leave.** Transfer ownership to another member first.
- **Can I undo a delete?** Files are removed from object storage immediately. The workspace row is hidden and purged after 30 days. Contact support within that window.

## Actions

Each opens a confirm dialog; delete requires typing the workspace name. Export downloads a file.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/workspace/export` | Owner JSON export |
| `POST /api/v1/workspace/leave`, `POST .../transfer`, `DELETE /api/v1/workspace` |  |

## Implementation map

`pages/settings/danger.vue`; i18n `danger.*`.
