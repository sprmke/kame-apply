# Route: `/notifications`

**Page:** `apps/web/app/pages/notifications.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Needs you | Manual | — | Done | Phase 10 |
| Inbox | Manual | Mark read | Done | Polling |

## Overview

Notification center: Needs-you items plus in-app inbox. Bell in the shell links here.

## User-facing knowledge

Shows what needs a decision and recent alerts. Mark items read when done.

## Sections

### Needs you

List from `GET /api/v1/needs-you` (tailor reviews, risk flags, failed runs, budget).

### Inbox

`GET /api/v1/notifications`; mark one or all read.

## API reference

| Call | Purpose |
| --- | --- |
| GET `/api/v1/needs-you` | Aggregation |
| GET `/api/v1/notifications` | Inbox |
| POST `/api/v1/notifications/{id}/read` | Mark read |
| POST `/api/v1/notifications/read-all` | Mark all |

## Implementation map

`apps/web/app/pages/notifications.vue`, `apps/api/app/notifications/`, i18n `notifications.*`.

## RBAC

Any member with `data.read` / `data.write`.
