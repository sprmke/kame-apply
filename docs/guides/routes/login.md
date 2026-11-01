# Route: `/login`

**Page:** `apps/web/app/pages/login.vue` · **Layout:** `auth` · **Access:** public (signed-in users are redirected to `/`)

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Email + password sign in | acceptance.spec.ts | Zod: email, password required | Done | Generic error for any failure |
| Google | acceptance.spec.ts (mocked in pytest) | n/a | Done | Button shows only when the server has Google credentials |
| `next` redirect | acceptance.spec.ts | `safeNext` allows same-origin paths only | Done |  |

## Overview

Returning users sign in with email and password, or with Google when the server is configured.

## User-facing knowledge

Sign in with the email and password you registered with. If sign-in fails you see one message whatever the cause, so nobody can probe which emails have accounts. After signing in you land where you were headed.

**Common user questions**

- **I forgot my password.** Use the link under the form. We email a reset link that works once for an hour.
- **Google says my email already has an account.** Sign in with your password, then link Google from Settings > Profile. We never merge accounts automatically.
- **I get 'Too many attempts'.** Sign-in is limited to 5 tries per email per 15 minutes. Wait, then try again.

## Form

Email and password fields, labelled, with inline translated errors. Submitting calls `auth.login`, loads workspaces, then goes to the `next` query path if it is a safe local path, else `/`.

## OAuth errors

`?error=<code>` from the Google callback shows the matching `errors.<code>` message above the form.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/auth/login` | Returns an access token and sets the HttpOnly refresh cookie |
| `GET /api/v1/auth/providers` | Whether to show the Google button |
| `GET /api/v1/auth/google/start` | Browser navigation that starts the OAuth flow |

## Implementation map

`pages/login.vue`, `stores/auth.ts`, `components/GoogleButton.vue`, `lib/next.ts`; i18n `auth.*`, `errors.*`.
