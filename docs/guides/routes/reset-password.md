# Route: `/reset-password?token=`

**Page:** `apps/web/app/pages/reset-password.vue` · **Layout:** `auth` · **Access:** public

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Set new password | acceptance.spec.ts | 10 to 128 characters | Done | Ends every signed-in device |

## Overview

Choose a new password from the emailed link.

## User-facing knowledge

Pick a new password. Every device that was signed in is signed out, so sign in again afterwards.

**Common user questions**

- **Why was I signed out everywhere?** A reset revokes all sessions on purpose, in case someone else had access.

## Form

New password with a hint; success shows a toast and goes to login.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/auth/password/reset` | Consumes the token, sets the password, revokes sessions |

## Implementation map

`pages/reset-password.vue`.
