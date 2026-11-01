# Phase 14: Release 1 hardening, free-tier deploy, personal beta

**Status:** Eng done · **Release:** R1 · **Depends on:** 13

**Human / prod remaining (not agent-closable):** dogfood log, uptime ≥ 99%, PRD baselines. Requires `applywave` first bring-up, then two weeks of real search.

## Goal

Release 1 runs in production on free infrastructure, is safe, observable, and recoverable, and Michael uses it for his real job search for two weeks before Release 2 starts.

## Tasks

- [x] Production Compose on Oracle A1 (or Hetzner fallback): Caddy (TLS), API, DBOS workers, Postgres 17 (tuned for 12 GB), ClamAV, backups (nightly `pg_dump` → R2, 14 daily + 8 weekly, restore drill), log rotation, unattended upgrades, firewall, fail2ban.
  - Compose/Caddy/Postgres/ClamAV/backup: `infra/docker-compose.prod.yml`, `infra/caddy/`, `infra/postgres/prod/`, `infra/backup/`
  - Host harden: `infra/host/harden.sh`
  - Local restore drill: `pnpm run restore:drill:local`
- [x] Web on Cloudflare Pages; API domain; CORS; CSP headers; HSTS.
  - `deploy:web:*`, Nuxt `routeRules` CSP, Caddy + API HSTS
- [x] Deploy scripts `deploy:*` + migrations with pre-deploy backup; unlock word enforcement; rollback script.
  - `scripts/deploy/*`, root `package.json` scripts, `rollback-api.sh`
- [x] Observability: Sentry (web/api/extension), uptime check (free tier), source-health and workflow dashboards (admin), AI cost dashboard.
  - API Sentry existing; web `@sentry/vue` plugin; extension DSN hook
  - Ops dashboard: `GET /api/v1/ops/dashboard` + `/settings/ops`
  - Uptime: operator configures free check (UptimeRobot/Better Stack) against `/healthz` after first deploy (see below)
- [x] Security pass: SSRF in link resolver / AI base URLs (block private + metadata), trusted proxies, dependency/security tests, rate limits (existing).
  - `app/core/ssrf.py`, `tests/test_ssrf.py`, `TRUSTED_PROXIES`
  - `security-auditor` on Phase 14 diff: fixed redirect SSRF in `links.py`, `:5432` unlock bypass, feedback digit/PII guard
- [x] Performance budget: document + smoke path (job list p95 / LCP measured after prod traffic; local gate is `ci:quality` + existing list endpoints).
- [x] Accessibility audit smoke: `pnpm run check:a11y-smoke` (h1 / skip-link on key routes when web is up).
- [x] Legal pages: privacy policy, terms, data deletion; no cookie banner (no third-party trackers by default).
- [x] Data lifecycle: workspace export/delete end-to-end incl. R2 purge.
- [x] Beta feedback loop: in-app feedback button → GitHub issue (no PII) when `GITHUB_FEEDBACK_TOKEN` set.

## Dogfood checklist (2 weeks, real search) — human + live prod

Template: `docs/workflow/in-progress/phase-14-dogfood-log.md`

- [ ] ≥ 3 Tracks running on schedules; ≥ 20 tailored applications; record interview rate vs kame-hunt baseline.
- [ ] Log every friction point; fix P0/P1 before Release 2.

## Exit criteria

- [x] Restore drill succeeded locally (`pnpm run restore:drill:local`).
- [ ] Uptime ≥ 99% over the beta (requires prod + free uptime monitor after `applywave` deploy).
- [x] No known cross-tenant or PII gaps introduced this phase (export omits secrets; feedback strips email/long digits; SSRF blocks private ranges).
- [ ] PRD success-metric baselines recorded during dogfood.

## Operator notes (first prod bring-up)

1. Provision VM; run `infra/host/harden.sh`.
2. Copy secrets to `/etc/kame-apply/api.env` (never commit).
3. `APPLYWAVE=applywave pnpm run deploy:api:prod` then `migrate:prod` then `deploy:web:prod`.
4. Point DNS; confirm Caddy TLS; hit `/healthz` and `/readyz`.
5. Configure free uptime check on `https://api…/healthz`.
6. Start dogfood log.
