# Route: `/settings/notifications`

**Page:** `apps/web/app/pages/settings/notifications.vue` · **Layout:** settings · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Prefs matrix | Manual | channel × event | Done | Phase 10 |
| Unsubscribe | Manual | — | Done | Disables email |

## Overview

Per-event in-app and email preferences for the current user in the workspace. The page lede explains that this controls what we send and where.

## User-facing knowledge

Choose which alerts arrive in-app or by email. Unsubscribe turns email off for this workspace.

## API reference

| Call | Purpose |
| --- | --- |
| GET/PUT `/api/v1/notification-prefs` | Matrix |
| POST `/api/v1/notification-prefs/unsubscribe-email` | Disable email |

## Implementation map

`apps/web/app/pages/settings/notifications.vue`, `apps/api/app/notifications/service.py`.
