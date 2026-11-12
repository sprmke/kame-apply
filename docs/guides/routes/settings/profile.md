# Route: `/settings/profile`

**Page:** `apps/web/app/pages/settings/profile.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Your details | acceptance.spec.ts | timezone must be a real IANA zone | Done | Save disabled until changed |
| Appearance | acceptance.spec.ts | n/a | Done | Stored in this browser |
| Connected accounts | pytest (mocked) | n/a | Done | Needs server credentials; unlink asks first |

## Overview

Three cards: your details, appearance, and connected accounts. This page changes the person, not the workspace.

## User-facing knowledge

Times across the app show in your timezone. Theme follows your system until you pick light or dark. Link Google to sign in with it.

**Common user questions**

- **Why is Link missing?** Google sign-in is not configured on this server.
- **Why does linking say to confirm my email?** Linking is allowed only for confirmed accounts. Use the link we emailed, or resend it from Today.

## Details

Email (read only), name, timezone. Save stays disabled until something changed.

## Appearance

System, light or dark. Applies immediately on this device.

## Connected accounts

Google link status. Unlinking opens a confirm dialog that says password sign-in still works.

## API reference

| Call | Purpose |
| --- | --- |
| `GET|PATCH /api/v1/me` | Profile |
| `POST /api/v1/auth/google/link` | Returns the Google URL (needs a confirmed email) |
| `DELETE /api/v1/auth/google/link` | Unlinks Google (needs a password on the account) |

## Implementation map

`pages/settings/profile.vue`, `composables/useTheme.ts`; i18n `profile.*`, `theme.*`; `FnSectionCard`.
