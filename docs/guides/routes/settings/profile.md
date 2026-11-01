# Route: `/settings/profile`

**Page:** `apps/web/app/pages/settings/profile.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Name and timezone | acceptance.spec.ts | timezone must be a real IANA zone | Done |  |
| Theme | acceptance.spec.ts | n/a | Done | Stored in this browser |
| Google link | pytest (mocked) | n/a | Done | Needs server credentials |

## Overview

Your name, timezone, theme and connected accounts.

## User-facing knowledge

Times across the app show in your timezone. Theme follows your system until you pick light or dark. Link Google to sign in with it.

**Common user questions**

- **Why is Link missing?** Google sign-in is not configured on this server.
- **Why does linking say to confirm my email?** Linking is allowed only for confirmed accounts. Use the link we emailed, or resend it from Today.

## Details

Email (read only), name, timezone.

## Theme

System, light or dark.

## Connected accounts

Google link status.

## API reference

| Call | Purpose |
| --- | --- |
| `GET|PATCH /api/v1/me` | Profile |
| `POST /api/v1/auth/google/link` | Returns the Google URL (needs a confirmed email) |
| `DELETE /api/v1/auth/google/link` | Unlinks Google (needs a password on the account) |

## Implementation map

`pages/settings/profile.vue`, `composables/useTheme.ts`; i18n `profile.*`, `theme.*`.
