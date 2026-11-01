# Route: `/settings/sessions`

**Page:** `apps/web/app/pages/settings/sessions.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| List and revoke | acceptance.spec.ts | n/a | Done |  |

## Overview

Devices signed in to your account.

## User-facing knowledge

Sign out any device you do not recognise. The current device is marked.

**Common user questions**

- **What happens when I sign a device out?** Its access stops immediately, not when its token expires.

## List

Browser and OS, IP, last used; Sign out on other devices.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/me/sessions`, `DELETE /api/v1/me/sessions/{id}` |  |

## Implementation map

`pages/settings/sessions.vue`; i18n `sessions.*`.
