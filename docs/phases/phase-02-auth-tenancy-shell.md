# Phase 2: Auth, workspaces (multi-tenancy), RBAC, audit, AI providers, app shell & design system

**Status:** Done (not yet merged) · **Release:** R1 · **Depends on:** 1 · **Features:** tenancy (PRD §2), F16, shell for all

## Goal

Users can sign up, get a personal workspace, invite members, add an AI provider key with a budget, and navigate a responsive app shell built on the final design system. Tenant isolation is enforced at the app **and** database layer from day one.

## Acceptance scenarios

1. New user signs up with email/password or Google → lands in an auto-created personal workspace with the onboarding checklist.
2. User A cannot read, list, or modify any record of workspace B through any endpoint (automated cross-tenant suite proves it).
3. Owner adds a Gemini key (validated with a test call), sets a $5/month budget; usage meter shows $0.00.
4. Shell works at 375/820/1440 in light and dark; keyboard navigation reaches everything; ⌘K opens command palette.

## Tasks

### Backend
- [x] Auth (port kame-desk `fastapi-jwt-auth`): register, login, logout, refresh rotation with reuse detection, email verification, password reset (Resend; Mailpit locally), Google OAuth (Authlib, linking never merges silently), argon2id hashing, rate limits on auth routes, session list + revoke. See `architecture/auth.md`. Google needs `GOOGLE_CLIENT_ID/SECRET`; the flow is tested with a fake provider and has not run against real Google.
- [x] Workspaces (done in slice C, see `architecture/auth.md`): create on sign-up (`kind=personal`), rename, members, invitations (email link, expiry), roles `owner|admin|member|viewer`, transfer ownership, leave, delete (soft → hard after 30 days).
- [x] `WorkspaceContext` dependency: resolves `X-Workspace-Id`, verifies membership + role, sets `SET LOCAL app.workspace_id` + `app.user_id` in the transaction.
- [x] RLS: policies on every tenant table (template migration helper); app DB role without `BYPASSRLS`; separate migration role.
- [x] RBAC policy table (action × role), enforced server-side per endpoint (port `rbac-and-audit`).
- [x] `activity_log` writes through a service helper (`app/audit/service.py`); admin read endpoint `GET /activity` with filters.
- [x] AI module foundation (see `architecture/ai-providers.md`; re-wrap script is `python -m app.ops.rewrap_keks`): `ai_credentials` (envelope encryption: per-workspace DEK encrypted by master KEK from env), provider router (PydanticAI models for Gemini, OpenAI, Anthropic, Groq, OpenRouter, Ollama base URL), model tiers (`bulk`, `standard`, `premium`) mapped per workspace, `ai_usage` metering, **budget guard** (pre-call estimate + hard stop + friendly error), test-key endpoint.
- [x] Workspace limits (members, AI keys and budget enforced now; Tracks, sources, storage defined and enforced by their phases) with defaults.

### Frontend
- [x] **"Field Notes" design system** from [`design/design-system.md`](../design/design-system.md): the direction was already fully specified, so no variation exploration was run; the design-reviewer pass replaced it. Repo-root `DESIGN.md` is final. Do not import tokens, fonts, icons, or components from other Kame apps.
- [x] `packages/ui`: OKLCH tokens in Tailwind v4 `@theme` (paper/ink, persimmon, semantic, pencil, Track hues; light/dark/high-contrast), fonts (Instrument Sans, Newsreader, Martian Mono via `@nuxt/fonts`), base Vue components on Reka UI (button, input, select/combobox, chips, tabs, dialog/sheet, popover, tooltip, toast, menu, command bar, table, skeleton) + signature components stubs (proof mark, pencil text, route line, risk seal, grade ring, folder tab); token contrast check script in CI.
- [x] Living style guide route `/_design` (all components × states × light/dark) + Playwright visual snapshots at 375/820/1440.
- [x] App shell: 64px rail (Today, Tracks, Jobs, Applications, Runs, Studio, Answer Desk, Safety, Settings) with Needs-you badge, top bar (workspace switcher, Track switcher folder tabs, ⌘K, profile menu), mobile bottom bar with center Needs-you button, sheets on mobile, Reader/Workbench/Brief layout primitives, route skeletons, error boundary, 404, toasts.
- [x] Auth pages (sign up, login, verify, reset, invite accept), workspace settings (general, members, AI providers & budget with usage chart, danger zone), user settings (profile, sessions, timezone, notification placeholders).
- [x] Onboarding checklist component (Profile → Track → Extension) on Home empty state.
- [x] i18n from day one: message catalog (`@nuxtjs/i18n`), no hard-coded UI strings, locale-aware dates/numbers/currency (`Intl`), RTL-safe layout utilities; ship English first. API error codes are stable keys, not English sentences.

## Data model

`users`, `user_sessions`, `workspaces`, `workspace_members`, `invitations`, `ai_credentials`, `ai_usage`, `workspace_limits`, `activity_log` (from Phase 1), RLS policies.

## API

`/auth/*`, `/me`, `/workspaces`, `/workspace` and `/workspace/members|invitations|transfer|leave` (active workspace via `X-Workspace-Id`), `/invitations/accept`, `/ai/credentials`, `/ai/credentials/{id}/test`, `/ai/usage`, `/activity`.

## Edge cases & failure modes

- Google account email equals an existing password account → link after verifying ownership, never silently merge.
- Last owner tries to leave/delete → blocked with explanation.
- Invite to an email that already has an account → joins existing user; invite reuse/expiry.
- Budget reached mid-workflow → workflow pauses with a `budget` reason (not fail); user sees "AI budget reached" in Needs-you with "raise budget" action.
- Invalid/revoked provider key → mark credential `invalid`, notify, fall back to another configured provider only if the user enabled fallback.
- No AI key at all → features that need AI show a clear setup prompt; non-AI features (discovery, rule scoring) still work. Optional local Ollama path documented.
- Clock skew/refresh race on multiple tabs → refresh with single-flight on the client.

## Security

- Cross-tenant test suite (parametrized over every router) is mandatory and runs in CI from now on.
- Secrets never logged; keys shown masked; master key rotation procedure documented.
- `security-auditor` agent review required for this phase.

## Testing

pytest: auth flows, token rotation/reuse, RBAC matrix, RLS (raw SQL with wrong `app.workspace_id` returns 0 rows), budget guard; Vitest: shell components; Playwright E2E: sign-up → onboarding → add key → invite member.

## Docs to update

`architecture/overview.md` §4 (any changes), `docs/architecture/auth.md` (new), `docs/guides/routes/*.md` for each new page, `DESIGN.md`.

## Exit criteria

- [x] Acceptance scenarios 1–4 pass in the running app (`e2e/acceptance.spec.ts`, `e2e/shell.spec.ts`: 27 Playwright tests, including a live Gemini key check).
- [x] Cross-tenant suite + RLS tests green (`pnpm run ci:quality`; GitHub Actions has not run on a real PR yet, a Phase 1 item).
- [x] Design screenshots reviewed by `design-reviewer`; no horizontal scroll at 375. The review failed the first pass on 44px targets and one-persimmon; both fixed and covered by `check:design-slop` and an e2e test. `security-auditor` reviewed too; see `architecture/security-review-phase-2.md`.
