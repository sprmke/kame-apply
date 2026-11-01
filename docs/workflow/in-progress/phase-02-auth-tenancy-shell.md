# Phase 2: Auth, tenancy, RBAC, AI providers, shell, design system (scratchpad)

**Branch:** `phase/02-auth-tenancy-shell` · **Started:** 2026-10-28 · **Phase file:** `docs/phases/phase-02-auth-tenancy-shell.md`

Phase 1 open items (Oracle spike, CI on a PR, spike-decision exit criterion) stay open by agreement; they do not block this phase.

## Plan (vertical slices, risk first)

1. [x] A. Tenancy foundation: roles (migration/app, no BYPASSRLS), `users`, `workspaces`, `workspace_members`, RLS template helper, `WorkspaceContext`, RBAC table, activity-log service, cross-tenant test harness (parametrized over routers)
2. [x] B. Auth (password): register/login/logout, argon2id, JWT access + refresh rotation with reuse detection, sessions list/revoke, rate limits, email verify + reset (Mailpit). **Google OAuth deferred until credentials exist.**
3. [x] C. Workspaces API: personal workspace on sign-up, rename, members, invitations, transfer/leave/delete, limits
4. [x] D. AI foundation: `ai_credentials` envelope encryption, provider router, tiers, `ai_usage`, budget guard, test-key endpoint
5. [x] E. Design system in `packages/ui` (tokens complete, base components, signature stubs, `/_design`, contrast script, visual snapshots) and root `DESIGN.md`
6. [x] F. App shell (rail, top bar, mobile bar, layouts, ⌘K), auth pages, settings pages, onboarding checklist, i18n
7. [x] G. Playwright E2E (sign-up -> onboarding -> add key -> invite), docs (`architecture/auth.md`, route guides), `security-auditor` + `design-reviewer` reviews, screenshots

## Decisions

- Real RLS testing needs a non-owner, non-BYPASSRLS app role; the test suite must connect as that role, otherwise RLS tests prove nothing (table owners bypass RLS unless FORCE is set, and superusers always bypass).
- Postgres local superuser `kame_apply` becomes the migration role; the app role is `kame_apply_app`.

## Open questions

- Google OAuth client id/secret and a Gemini/Groq key are needed from the owner for slices B and D acceptance checks (placed in `apps/api/.env`, never in chat).

## Slice A notes

- Built: roles + `ensure-db-roles.sh`, migration 0002 (users, workspaces, workspace_members, RLS, activity_log RLS + revoked UPDATE/DELETE), `app/core/{rls,rbac,security}.py`, `app/audit/service.py`, tenancy fixtures, 56 passing tests.
- Found by tests: downgrade order bug (policy dependency), fixture deadlock (open txn vs DROP TABLE), `ON DELETE SET NULL` FK would have violated the append-only trigger (removed).
- Route-coverage test fails any `/api/v1` route that does not depend on `workspace_context` unless allowlisted in `tests/test_route_coverage.py::PUBLIC_OR_USER_SCOPED`; slice B must add `/api/v1/auth` and `/api/v1/me` there with reasons.
- `users` is global and not RLS-protected; only auth services may query it. Revisit with a column-restricted view if tenant code ever needs user names.

## Slice B notes

- Built: migration 0003 (user_sessions, refresh_tokens, auth_tokens; ro role cannot read them or password_hash), `app/auth/{passwords,tokens,service,router,schemas}.py`, `app/core/{mail,ratelimit}.py`, real `current_principal`, platform audit rows (`record_platform`), 75 tests, docs in `architecture/auth.md`.
- Found while reviewing: multi-tab refresh race would have killed sessions as "reuse"; added a 10 s grace window.
- Reuse revocation must commit, so refresh returns a 401 response instead of raising (get_db rolls back on exceptions).
- Rate limiter is in-memory per instance; client IP is the proxy IP until Phase 14 configures forwarded headers.
- Not done: Google OAuth; Mailpit manual check of the rendered emails (tests use an in-memory outbox).

## Slice C notes

- Built: migration 0004 (invitations + token-scoped RLS policy), `app/workspaces/{service,router,schemas}.py`, personal workspace on register, `audit.record_in_workspace`, rank-based role rules, 91 tests total.
- Deviation: tenant routes are `/workspace/...` keyed by the header, not `/workspaces/{id}/...`.
- Not done: workspace limits table (only a constant cap of 5 owned teams), 30-day hard-delete job (Phase 10), invite preview endpoint (add with the invite accept page in slice F).

## Slice D notes

- Built: migration 0005, `app/ai/{crypto,providers,service,router,schemas,models}.py`, 111 tests + 2 opt-in live tests (Gemini and Groq verified against the real APIs, valid and invalid keys).
- Live testing found: Gemini 2.5 flash-lite/pro are retired for new keys (defaults moved to 3.5 flash-lite, 3.5 flash, 3.1 pro preview); Gemini signals a bad key with HTTP 400 `API_KEY_INVALID`; reasoning models need output-token headroom.
- Dev keys are in `apps/api/.env` (gitignored, mode 600). They were pasted into the chat, so treat them as exposed and rotate before any shared use.
- Not done: KEK rewrap script, per-tier UI, no feature calls `run_text` yet (Phase 3 is first).

## Slices E to G notes

- Backend leftovers closed: Google OAuth (fake-provider tests), `GET /activity`, `workspace_limits`, KEK rewrap script. Found by tests: membership queries leaked a user's own rows from other workspaces until filtered by workspace.
- Frontend: tokens (light, dark, high contrast, contrast script), 22 `Fn*` components, `/_design`, shell, auth, settings and onboarding pages, i18n catalog with integrity tests, generated Zod schemas for forms, 27 Playwright tests, visual snapshots, review screenshots in `docs/design/screenshots/phase-02/`.
- Review outcomes: design-reviewer found 44px targets (root font 14px made `min-h-11` 38px; fixed with `--spacing: 4px`) and a second persimmon; security-auditor found a pre-hijack path via unverified email, SSRF gaps and a fail-open environment default. All fixed or accepted in `docs/architecture/security-review-phase-2.md`.
- Tests: 144 pytest (+2 live opt-in), 21 UI, 5 web unit, 27 Playwright.
- Left for later by design: Google against real credentials, Track switcher and Needs-you content (Phases 4 and 11), enforcement of Tracks/sources/storage limits, 30 day hard delete job (Phase 10), forwarded-IP handling and Postgres rate limits (Phase 14).

## Pending items (as of 2026-11-01)

- Phase 1: Oracle spike, CI on a real PR, spike-decision exit criterion.
- Phase 0: leftovers delegated to the opencode agents, unverified.
- Phase 2: nothing open except real-Google verification and a PR.
- Nothing is committed.
