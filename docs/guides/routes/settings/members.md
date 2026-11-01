# Route: `/settings/members`

**Page:** `apps/web/app/pages/settings/members.vue` · **Layout:** `default` · **Access:** signed in; managing needs owner or admin

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Member list | acceptance.spec.ts | n/a | Done |  |
| Invite | acceptance.spec.ts | email, role below your own | Done | Seat cap counts pending invites |
| Change role / remove | pytest `test_workspaces.py` | Rank rules enforced server side | Done | UI hides what you cannot do |

## Overview

See who is in the workspace, invite people, change roles, remove members.

## User-facing knowledge

You can manage only people below your own role. Admins manage members and viewers; owners also manage admins. Ownership moves only through Transfer in the Danger zone.

**Common user questions**

- **Why can't I make someone an owner here?** Ownership is transferred, not granted. See Danger zone.
- **Why can't I invite another admin?** Admins can invite roles below admin. Ask an owner.
- **What are seats?** The workspace caps members; pending invitations count until accepted or revoked.

## Table

Member, role, joined date, actions menu.

## Pending invites

Email, role, expiry, Revoke.

## Dialogs

Invite (email, role) and a remove confirmation.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/workspace/members` | List |
| `PATCH|DELETE /api/v1/workspace/members/{user_id}` | Role change, removal |
| `GET|POST /api/v1/workspace/invitations`, `DELETE .../{id}` | Invitations |
| `GET /api/v1/workspace/limits` | Seats |

## Implementation map

`pages/settings/members.vue`; i18n `members.*`, `role.*`.
