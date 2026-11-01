# Route: `/forgot-password`

**Page:** `apps/web/app/pages/forgot-password.vue` · **Layout:** `auth` · **Access:** public

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Request link | acceptance.spec.ts | email | Done | Always answers the same |

## Overview

Starts a password reset.

## User-facing knowledge

Enter your email. We always say a link is on its way if the address has an account, so the page never reveals who is registered.

**Common user questions**

- **I did not get an email.** Check spam, then try again. Requests are limited to 3 per email per hour.

## Form

One email field; success replaces the form with a status message.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/auth/password/forgot` | Always 202 |

## Implementation map

`pages/forgot-password.vue`.
