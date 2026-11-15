# Route: `/settings/sessions`

**Page:** `apps/web/app/pages/settings/sessions.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Device list | acceptance.spec.ts | n/a | Done | Card with one row per session |
| Sign out another device | Manual | confirm dialog | Done | Access stops immediately |
| Load and error states | Manual | — | Done | Retry on failure |

## Overview

Devices signed in to your account, newest activity first, in one section card.

## User-facing knowledge

Sign out any device you do not recognise. The current device is marked and has no sign-out control.

**Common user questions**

- **What happens when I sign a device out?** Its access stops immediately, not when its token expires.
- **Why does the address say "This network"?** Local and loopback addresses are shown as the network instead of a number.

## List

Browser and OS, current badge, address (or "This network"), last used. Sign out is a quiet button that opens a confirm dialog, so one stray click cannot drop a session.

## States

Loading: skeleton. Empty and error: one line plus the next action (retry on error).

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/me/sessions`, `DELETE /api/v1/me/sessions/{id}` |  |

## Implementation map

`pages/settings/sessions.vue`; i18n `sessions.*`; `FnSectionCard`.
