# Route: `/settings/notifications`

**Page:** `apps/web/app/pages/settings/notifications.vue` · **Layout:** default · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Prefs matrix | Manual | channel × event | Done | Phase 10 |
| Turn off all email | Manual | confirm dialog | Done | Disables email for the workspace |
| Load and error states | Manual | — | Done | Retry on failure |

## Overview

Per-event in-app and email preferences for the current user in the workspace. One card, one table, six events, two channels. A summary line states how many events currently send email.

## User-facing knowledge

Choose which alerts arrive in the app, by email, or both. **Turn off all email** stops every email at once and asks first; the app keeps working. Saving is available only after a change.

## Sections

- **What we send.** Table with event rows and In-app / Email columns. Every checkbox has an accessible label such as "Strong match, Email".
- **Summary.** "Email is on for {n} of 6." Recomputes live.
- **Footer.** Save (disabled until dirty) and Turn off all email (confirm dialog).

## States

Loading: skeleton. Error: message plus **Try again**. Success: toast on save.

## API reference

| Call | Purpose |
| --- | --- |
| GET/PUT `/api/v1/notification-prefs` | Matrix |
| POST `/api/v1/notification-prefs/unsubscribe-email` | Disable email |

## Implementation map

`apps/web/app/pages/settings/notifications.vue`, `apps/api/app/notifications/service.py`. Primitives: `FnSectionCard`, `FnCheckbox` (with `hide-label`), `FnSummaryLine`, `FnDialog`.


## Recommended defaults (2026-11-13)

**Use recommended** removes this user's overrides (`POST /notification-prefs/reset`) so the defaults apply again: in-app for everything, email for the digest, needs-you, risk, and budget. Run-failed stays in-app only.
