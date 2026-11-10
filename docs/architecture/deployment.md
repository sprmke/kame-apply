# Deployment and local environment

**Status:** local environment real (Phase 1); hosted Compose/Caddy/backup/deploy scripts landed (Phase 14). Stack and hosting rationale: [`../tech-stack.md`](../tech-stack.md) §5.

## 1. Local development

| Service | How it runs | Port (host) | Credentials (local only) |
| --- | --- | --- | --- |
| Postgres 17 + pgvector | `infra/docker-compose.dev.yml` (`pgvector/pgvector:pg17`) | 5442 | owner/migration role `kame_apply` / `kame_apply_local_only`; runtime role `kame_apply_app` / `kame_apply_app_local_only` (NOBYPASSRLS); dbs `kame_apply`, `kame_apply_test` |
| Read-only role for the `postgres` MCP | created by `infra/postgres/init/01-roles-and-test-db.sql` on a fresh volume | 5442 | `kame_apply_ro` / `kame_apply_ro_local_only` |
| MinIO (R2 stand-in) | compose | 9100 (S3), 9101 (console) | `kame_apply` / `kame_apply_local_only` |
| Mailpit (SMTP sink) | compose | 1125 (SMTP), 8125 (UI) | none |
| API | `pnpm run dev:api` (uvicorn `--reload`) | 8100 (`/docs`, `/healthz`, `/readyz`) | `apps/api/.env` |
| Web | `pnpm run dev:web` (Nuxt) | 3100 | none |

All ports bind to `127.0.0.1` and avoid the other Kame apps (3000/8000/5432). `pnpm run dev:docker` starts the containers and waits for health; `pnpm run dev` (or `./dev.sh`) also migrates and runs API + web together.

First run: `pnpm install`, `uv sync --all-packages`, copy `apps/api/.env.example` to `apps/api/.env`, `pnpm run dev:docker`, `pnpm run dev`.

**Editor tasks (`.vscode/`):** `tasks.json` mirrors the commands above for Cursor and VS Code under `Run Task` (Dev, DB, Quality, Test, API client, dev deploy). `Dev: Start everything` is the default build task (`⇧⌘B`). `launch.json` adds API debugging (`debugpy` against `.venv/bin/python`) and Chrome debugging against `:3100`. Prod deploy, migrate, and rollback are deliberately absent from the task list; run those from the CLI with the unlock word. Task PATH additions live in `.vscode/settings.json` (`terminal.integrated.env.osx`).

The init SQL runs only on a **fresh volume**. If the volume predates a change to it, run `pnpm run stop:docker`, remove the `kame-apply-dev_pgdata` volume, and start again (or apply the SQL by hand).

## 2. Database and migrations

- Alembic in `apps/api/migrations/`; `pnpm run db:migrate` (upgrade head), `pnpm run db:migrate:new -- "message"` (autogenerate; review by hand), `pnpm run db:reset:local` (drops the local DB, refuses non-local URLs).
- **Two roles.** Alembic runs as the owner (`MIGRATION_DATABASE_URL`); the API connects as `kame_apply_app` (`DATABASE_URL`), which is not a superuser and has no `BYPASSRLS`. Table owners and superusers skip RLS, so the API must never connect as the owner. `scripts/dev/ensure-db-roles.sh` (run by `dev:docker` and `db:reset:local`) creates the roles and default grants idempotently; tests assert the runtime role cannot bypass RLS.
- Migration 0002 adds `users`, `workspaces`, `workspace_members` and the RLS foundation (`app/core/rls.py`: `tenant_rls_sql()` for tenant tables; policies fail closed when `app.workspace_id`/`app.user_id` are unset or empty). `activity_log` is RLS-scoped and the app role has no UPDATE/DELETE/TRUNCATE on it.
- Migration 0001 enables `vector`, `pg_trgm`, `citext`, `pgcrypto` and creates `activity_log` with triggers that reject UPDATE, DELETE, and TRUNCATE.
- The test suite uses the `kame_apply_test` database and runs `downgrade base` then `upgrade head` at session start, so the downgrade path is exercised on every run.
- Taxonomy seed (curated occupations/skills + 40+ Track templates + FX fallback): `pnpm run db:seed` (`scripts/taxonomy/refresh.py --seed --fx`). Full ESCO/O*NET dumps: same script with `--esco-dir` / `--onet-dir` (owner DB role). See [`criteria-and-taxonomy.md`](./criteria-and-taxonomy.md).
- Prod migrations and deploys require the unlock word (`no-prod-deploy.mdc`).

## 3. API surface conventions

- Health: `GET /healthz` (liveness), `GET /readyz` (DB check, 503 when down). Both are excluded from request logs.
- Everything else under `/api/v1`. Errors always use `{"error": {"code", "message", "details"}}`. Every response carries `X-Request-ID` (a caller-supplied id is kept only if short and plain ASCII).
- Docs and OpenAPI are disabled when `ENVIRONMENT=prod`.
- Sentry initialises only when `SENTRY_DSN` is set, with `send_default_pii=False` and no request bodies. Logs are JSON with request id and a key-based secret redactor.
- The OpenAPI schema is exported by `app.export_openapi` and turned into `packages/api-client` by `pnpm run gen:api-client`; CI fails if the committed client is stale.

## 4. CI

`.github/workflows/ci.yml`: tooling and policy checks (AI tooling sync, hook tests, filenames, stack terminology), Python (ruff, format, basedpyright, pytest against a pgvector service), web (ESLint, type-check, Vitest, build for web/ui/extension, API client drift). Before pytest, `scripts/dev/ci-prepare-postgres.sh` creates `kame_apply_app` / `kame_apply_ro` (the service image has no compose init). `pnpm run ci:quality` runs the same gates locally.

## 5. Hosted layout (Phase 14)

**Blocked without unlock:** any `deploy:*:prod`, `migrate:prod`, or write against a hosted `DATABASE_URL` needs the user to type **`applywave`** in the same message (`no-prod-deploy.mdc`). Dogfood / uptime / PRD baselines need that first bring-up plus two weeks of real use (`docs/workflow/in-progress/phase-14-dogfood-log.md`).

Oracle Always Free A1 (fallback Hetzner CAX11) running Docker Compose behind Caddy:

| Piece | Path / command |
| --- | --- |
| Compose | `infra/docker-compose.prod.yml` (`caddy`, `api`, `runner`, `postgres`, `clamav`, `backup`) |
| Caddy TLS + headers | `infra/caddy/Caddyfile` (HSTS, CSP for API) |
| Postgres tune | `infra/postgres/prod/postgresql.conf` |
| Nightly dump → R2 | `infra/backup/backup-loop.sh` (14 daily + 8 weekly). Requires `MIGRATION_DATABASE_URL` (owner role; the app role dumps empty under RLS), verifies the dump with `pg_restore --list`, prunes old objects, and exits after three consecutive failures so the supervisor alerts. |
| Host harden | `infra/host/harden.sh` (ufw, fail2ban, unattended-upgrades, log rotate) |
| API image | `apps/api/Dockerfile` |
| Deploy API | `pnpm run deploy:api:dev\|prod` → `scripts/deploy/deploy-api.sh` (set `KAME_REGISTRY` to push, otherwise the image is shipped over SSH; `DEPLOY_HEALTH_URL` adds a post-deploy check; dev sets `KAME_ENVIRONMENT=dev`, prod defaults to `prod`) |
| Deploy runner | `pnpm run deploy:runner:dev\|prod` → `scripts/deploy/deploy-runner.sh`; secrets in `/etc/kame-apply/runner.env` (`KAME_RUNNER_TOKEN`, `KAME_RUNNER_WORKSPACE_ID`) |
| Deploy web | `pnpm run deploy:web:dev\|prod` (Nuxt generate → Cloudflare Pages). Requires `NUXT_PUBLIC_API_BASE`; `CF_PAGES_PROJECT` publishes with wrangler. |
| Database roles | `pnpm run db:roles:host:dev\|prod` creates the RLS-restricted `kame_apply_app` role on the host (the prod Compose no longer mounts the local init SQL). |
| Migrate | `pnpm run migrate:dev\|prod` against a reachable database URL, or `pnpm run migrate:host:dev\|prod` to run Alembic inside the API container over SSH (the Compose database is not exposed). Prod needs `applywave`. |
| Scheduler | `SCHEDULER_ENABLED` (default true). The API process runs the minute tick under a Postgres advisory lock (a second worker skips), reaps lost runs, and purges workspaces past the 30-day window at 03:00. |
| Backup / restore | `backup:db:*`, `rollback:db:*`, `scripts/deploy/rollback-api.sh` |
| Local restore drill | `pnpm run restore:drill:local` |

Prod deploys and remote migrations require the unlock word in the same command (`APPLYWAVE=applywave`, see `no-prod-deploy.mdc`). Spike 2 ([`spikes/02-oracle-always-free.md`](./spikes/02-oracle-always-free.md)) is the gate for VM sizing. The complete variable list and first-deploy runbook are in [`configuration.md`](./configuration.md).

**Web headers:** Nuxt `routeRules` set CSP, HSTS-ready frame/options, nosniff. API middleware adds the same class of headers; HSTS when `X-Forwarded-Proto: https`.

**Trusted proxies:** `TRUSTED_PROXIES` (comma CIDRs). Rate limits use `X-Real-IP` / `X-Forwarded-For` only when the peer is trusted.

**Uptime / dogfood:** free-tier uptime check and the 2-week personal beta are operator steps after the first prod deploy (see phase file). In-repo deliverable is scripts + checklists, not live SLOs.

## Auth, mail and AI environment (Phase 2)

| Variable | Purpose | Notes |
| --- | --- | --- |
| `JWT_SECRET` | Signs access tokens and the OAuth state cookie | Prod refuses the dev default or a value under 32 characters |
| `COOKIE_SECURE` | `Secure` flag on cookies | Must be true in prod |
| `MASTER_KEK` | Base64 32-byte key wrapping per-workspace data keys | Prod refuses the public dev key; rotate with `python -m app.ops.rewrap_keks` |
| `WEB_BASE_URL`, `API_BASE_URL` | Links in emails; OAuth redirect URI | |
| `SMTP_HOST`, `SMTP_PORT`, `MAIL_FROM` | Mail via Mailpit locally (UI on 8125) | |
| `RESEND_API_KEY` | Mail in prod (Resend) | Overrides SMTP when set |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google sign-in | Optional; endpoints 404 without them |
| `AUTH_RATE_LIMIT_ENABLED` | In-process auth rate limits | Off only for e2e runs |
| `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_REGION` | Object storage (MinIO locally, R2 in prod) | Tests use in-memory storage; API creates the bucket on startup when missing |
| `TRUSTED_PROXIES` | CIDRs allowed to set `X-Forwarded-For` / `X-Real-IP` | Compose defaults to RFC1918 ranges |
| `GITHUB_FEEDBACK_TOKEN`, `GITHUB_FEEDBACK_REPO` | In-app feedback → GitHub issue | Optional; without token, feedback is audit-logged only |
| `NUXT_PUBLIC_SENTRY_DSN` / `SENTRY_DSN` | Browser / API Sentry | `send_default_pii=False`; no request bodies |

Migrations 0003 to 0006 add auth tables, invitations, AI tables, workspace limits and OAuth identities. Migration 0008 adds career profile tables; 0009 adds `documents`; 0010 adds `answer_bank`; 0011 adds `voice_profiles`; 0012 adds `profile_proposals`. They are additive; no backfill.

### Data lifecycle (Phase 14)

| Action | Endpoint / behavior |
| --- | --- |
| Export | `GET /api/v1/workspace/export` (owner). JSON without secrets/tokens/encrypted keys. |
| Delete team workspace | `DELETE /api/v1/workspace`. Soft-deletes; purges `ws/<id>/` in R2 immediately; hard purge of rows after 30 days. |
| Feedback | `POST /api/v1/feedback` (no email/long digit runs). Optional GitHub issue. |
| Ops dashboard | `GET /api/v1/ops/dashboard` (admin): sources, recent runs, AI cost. |
