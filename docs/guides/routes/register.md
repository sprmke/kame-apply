# Route: `/register`

**Page:** `apps/web/app/pages/register.vue` · **Layout:** `auth` · **Access:** public

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Create account | acceptance.spec.ts | email, password 10 to 128 characters, optional name | Done | Server returns 409 for an existing email |

## Overview

New users create an account. A personal workspace is created for them automatically.

## User-facing knowledge

Enter your email and a password of at least 10 characters (no other rules). You are signed in straight away and land on Today with a short setup list. We email a confirmation link; you can use the app before confirming.

**Common user questions**

- **Why does it say the email already has an account?** That address is registered. Sign in, or reset the password.
- **Do I have to confirm my email?** Not to start. A banner on Today reminds you and lets you resend the link.

## Form

Name (optional), email, password with a hint. A taken email maps to the email field error.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/auth/register` | Creates user, personal workspace, session; sends the verification email |

## Implementation map

`pages/register.vue`, `stores/auth.ts`, generated Zod `zRegisterIn` extended with the password rule; i18n `auth.*`, `validation.*`.
