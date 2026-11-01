# Auth

Phase 2. Password auth, Google OAuth, workspaces, limits and the activity feed are built. Code: `apps/api/app/auth/`, `app/core/security.py`.

## Tokens

| Token | Form | Lifetime | Stored |
| --- | --- | --- | --- |
| Access | JWT HS256 (`sub`, `sid`, `typ=access`), sent as `Authorization: Bearer` | 15 min | not stored |
| Refresh | 256-bit random, HttpOnly `kame_refresh` cookie, `SameSite=Lax`, path `/api/v1/auth`, `Secure` in prod | 30 days, rotated on every use | SHA-256 only |
| Email verify / password reset | 256-bit random in an emailed link | 48 h / 1 h, single use | SHA-256 only |

Every request re-checks that the access token's session (`sid`) is not revoked and the user is active, so revoking a session or deactivating a user takes effect immediately. Workspace membership and role are re-checked per request in `workspace_context`.

## Refresh rotation and reuse detection

Each refresh issues a new token and marks the old one used. Presenting a used token:

- within 10 s of its rotation: rejected with 401, session kept (two tabs racing);
- later: treated as theft. The whole session is revoked and `auth.refresh_reuse_detected` is logged.

Failure paths return a response instead of raising so the revocation commits.

## Endpoints (`/api/v1`)

`POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/verify-email`, `/auth/verify-email/resend`, `/auth/password/forgot`, `/auth/password/reset`; `GET|PATCH /me`, `GET /me/sessions`, `DELETE /me/sessions/{id}`. These are exempt from workspace scoping (allowlisted with reasons in `tests/test_route_coverage.py`).

- Login failures are one generic 401; an unknown email still runs one argon2 verification.
- `forgot` always answers 202. A reset or verification link voids earlier links of the same kind. A reset revokes every session and marks the email verified.
- Register on an existing email returns 409 `email_taken`. This reveals that the address has an account; it is rate limited and accepted for UX. Revisit if abuse shows up.
- Passwords: 10 to 128 characters, no composition rules, argon2id.

## Rate limits

In-process sliding window (`app/core/ratelimit.py`), per instance: register 5/h/IP; login 20/15 min/IP, 5/15 min per (email, IP) and 30/15 min per email (so a stranger cannot lock a victim out); invitations 20/h per user and 30/h per workspace; forgot 5/h/IP and 3/h/email; refresh 60/min/IP; reset 10/h/IP; resend 3/h/user. `client_ip` trusts `X-Real-IP` / `X-Forwarded-For` only when the peer matches `TRUSTED_PROXIES` (Compose sets RFC1918 ranges). Multiple API instances multiply the limits.

## Audit

Auth events are platform rows in `activity_log` (`workspace_id` NULL; tenants can insert but never read them): `auth.registered`, `auth.login`, `auth.email_verified`, `auth.password_reset`, `auth.session_revoked`, `auth.refresh_reuse_detected`, `user.updated`. Ids only, never emails, tokens, or passwords.

## Data

`user_sessions`, `refresh_tokens`, `auth_tokens` (migration 0003). Global tables, no RLS; only `app/auth/service.py` and `current_principal` read them. The read-only role used by the Postgres MCP server has no access to them and no access to `users.password_hash`.

## Config

`JWT_SECRET` (prod refuses to start with the default or a short one), `COOKIE_SECURE` (must be true in prod), `WEB_BASE_URL`, `SMTP_HOST/PORT` (Mailpit locally, UI on 8125), `RESEND_API_KEY` (prod mail), `MAIL_FROM`.

## Google OAuth

Authorization code flow with PKCE via Authlib (`app/auth/google.py`), behind a small class so tests substitute a fake. Needs `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and the redirect URI `{API_BASE_URL}/api/v1/auth/google/callback` registered in Google Cloud. Without credentials the endpoints answer 404 and the web app hides the button (`GET /auth/providers`).

- `GET /auth/google/start` redirects to Google and sets an HttpOnly `kame_oauth` cookie (10 min, path `/api/v1/auth/google`) holding a signed JWT with the state nonce, the PKCE verifier, and the user to link (if any). The `state` query parameter must match it.
- `GET /auth/google/callback` exchanges the code, then: known Google identity logs in; new verified email creates the account (email already verified, personal workspace); an email that matches an existing account is **refused** with `account_exists` (never merged silently); an unverified Google email is refused.
- `POST /auth/google/link` (signed in) returns the Google URL; the callback attaches the identity to that user. One identity maps to one user (`identity_in_use` otherwise).
- Every outcome redirects to the web app: success to `/auth/callback` (refresh cookie set), errors to `/login?error=<code>`.

## Workspace limits and activity feed

`workspace_limits` holds per-workspace caps (members, AI keys, Tracks, sources, storage, AI budget). A missing row means the defaults in `app/workspaces/models.py::DEFAULT_LIMITS`. The app role can only read the table, so a tenant cannot raise its own limits. Members (counting pending invitations), AI keys and AI budget are enforced now; Tracks, sources and storage are enforced by their phases. `GET /workspace/limits` returns caps and seats used.

`GET /activity` (owner and admin) lists the workspace audit trail newest first, filtered by action (exact, or a prefix ending in `.`), target type and actor, keyset paginated by `before`. RLS hides other workspaces and platform (auth) events.

A lesson worth keeping: the `workspace_members` policy also exposes a user's own memberships in other workspaces (needed to resolve the active workspace), so every membership query filters `workspace_id` explicitly. A test covers it.

## Workspaces (slice C)

Sign-up creates a `personal` workspace (owner). Team workspaces: `POST /workspaces` (max 5 owned). The active workspace is always the `X-Workspace-Id` header, so tenant routes live under `/api/v1/workspace/...` (not `/workspaces/{id}/...`), which removes any path-vs-header mismatch.

| Route | Action | Notes |
| --- | --- | --- |
| `GET/POST /workspaces` | user-scoped | list mine, create team |
| `GET/PATCH/DELETE /workspace` | read / update / delete | delete is a soft delete, team only; hard delete after 30 days is a Phase 10 job |
| `GET /workspace/members`, `PATCH/DELETE /workspace/members/{user_id}` | read / change_role / remove | actors manage only roles strictly below their own and never grant their own level |
| `POST /workspace/transfer`, `POST /workspace/leave` | transfer / leave | the owner must transfer before leaving; personal workspaces can be neither left nor transferred |
| `GET/POST /workspace/invitations`, `DELETE .../{id}` | members.invite | one live invitation per email, 7 days, single use |
| `POST /invitations/accept` | user-scoped | the account email must equal the invited email; works for existing accounts |

Invitation RLS: policy `invitation_access` exposes a row by active workspace, or by exactly the token hash held in the transaction-local `app.invite_token_hash`, which only the accept service sets.

The members list joins `users` for email and name, so a member can see co-members' emails. Nothing else from `users` is exposed to tenant code.

## Hardening from the security review

Verified email gates the risky actions: linking Google, signing in through a linked identity, sending invitations, and accepting one. Sessions also have a 90 day absolute lifetime. `ENVIRONMENT` defaults to `prod`, so dev secrets only work when `local` or `test` is set explicitly. Full list with dispositions: [`security-review-phase-2.md`](./security-review-phase-2.md).
