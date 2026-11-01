# Route: `/invite?token=`

**Page:** `apps/web/app/pages/invite.vue` · **Layout:** `auth` · **Access:** public (explains what to do when signed out)

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Accept invite | acceptance.spec.ts | Email must match the invited address | Done |  |

## Overview

Where an invited person joins a workspace.

## User-facing knowledge

Sign in or create an account using the email the invite was sent to, then press Join. The link works once and lasts 7 days.

**Common user questions**

- **It says the invitation was sent to a different email.** Sign in with the invited address. Invitations are bound to it.
- **It says to confirm my email.** Confirm the address first (link in your inbox, or resend from Today), then press Join again.
- **It says invalid or expired.** Ask an admin to send a new one.

## Signed out

Links to sign in or register that return here afterwards.

## Signed in

Shows the account and a Join button; on success the new workspace becomes active.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/invitations/accept` | Adds the membership with the invited role |

## Implementation map

`pages/invite.vue`; i18n `invite.*`.
