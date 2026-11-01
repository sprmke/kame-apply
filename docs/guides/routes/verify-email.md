# Route: `/verify-email?token=`

**Page:** `apps/web/app/pages/verify-email.vue` · **Layout:** `auth` · **Access:** public

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Confirm link | acceptance.spec.ts | Token single use, 48 h | Done |  |

## Overview

Landing page for the emailed confirmation link.

## User-facing knowledge

Open the link from the email. You see a confirmation or an error. A link works once; request a new one from the banner on Today if it expired.

**Common user questions**

- **The link says invalid.** It was already used or is older than 48 hours. Resend it from Today.

## Result

Calls the API on load and shows working, done, or failed.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/auth/verify-email` | Consumes the token and marks the email verified |
| `POST /api/v1/auth/verify-email/resend` | Sent from the Today banner; voids older links |

## Implementation map

`pages/verify-email.vue`, `components/VerifyEmailBanner.vue`.
