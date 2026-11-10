# Configuration and deploy runbook

Everything needed to run Kame Apply locally, on a dev host, or in production. Secrets are never committed; this page lists variable names and where each value comes from.

Canonical deployment layout: [`deployment.md`](./deployment.md). Prod deploys and remote writes need `applywave` in the same message (`no-prod-deploy.mdc`).

## 1. Environments

| Environment | API | Web | Database | Purpose |
| --- | --- | --- | --- | --- |
| Local | `pnpm run dev:api` on `:8100` | `pnpm run dev:web` on `:3100` | Compose Postgres on `:5442` | Development and E2E |
| Dev host | Compose `api` + Caddy on a VM | Cloudflare Pages | Compose Postgres on the same VM | Team testing before prod |
| Prod | Compose `api` + Caddy on a VM | Cloudflare Pages | Compose Postgres on the same VM | Real users |

`ENVIRONMENT` controls safety rails: `prod` refuses the public dev JWT/KEK and secure-cookie defaults and disables `/docs`; `dev` keeps docs enabled; `local` is the default for a checkout.

## 2. API environment (`apps/api/.env`, `/etc/kame-apply/api.env`)

Host templates: [`infra/kame-apply/api.env.example`](../../infra/kame-apply/api.env.example) and [`infra/kame-apply/runner.env.example`](../../infra/kame-apply/runner.env.example).

### Required in every deployed environment

| Variable | What it is | Where it comes from |
| --- | --- | --- |
| `ENVIRONMENT` | `dev` or `prod` | Set by the deploy script (`KAME_ENVIRONMENT`) |
| `DATABASE_URL` | Runtime role URL, no `BYPASSRLS` | `postgresql+asyncpg://kame_apply_app:<password>@postgres:5432/kame_apply` inside Compose |
| `MIGRATION_DATABASE_URL` | Owner role URL, used by Alembic and backups | `postgresql+asyncpg://kame_apply:<password>@postgres:5432/kame_apply` |
| `JWT_SECRET` | Signs access tokens and OAuth state | Generate: `openssl rand -base64 48` |
| `MASTER_KEK` | Base64 32-byte key wrapping workspace data keys | Generate: `python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"` |
| `COOKIE_SECURE` | `Secure` cookies | `true` on HTTPS hosts |
| `WEB_BASE_URL` | Links in emails and redirects | `https://app.example.com` |
| `API_BASE_URL` | OAuth redirect URI and public API links | `https://api.example.com` |
| `CORS_ORIGINS` | JSON list of allowed web origins | `["https://app.example.com"]` |
| `TRUSTED_PROXIES` | CIDRs allowed to set forwarded IPs | Compose defaults to RFC1918 ranges |
| `SCHEDULER_ENABLED` | Minute scheduler, reaper, purge | `true` |
| `AUTO_SUBMIT_ENABLED` | Global live auto-submit switch | `false` until the phase 19 gate |
| `AGENT_BRIDGE_ENABLED` | MCP bridge at `/mcp` | `true` unless unused |

### Storage (Cloudflare R2 in deployed environments)

| Variable | Value |
| --- | --- |
| `S3_ENDPOINT_URL` | `https://<account-id>.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | R2 API token with object read/write |
| `S3_BUCKET` | Bucket name, e.g. `kame-apply` |
| `S3_REGION` | `auto` |

Create the bucket once in the Cloudflare dashboard. Local dev uses MinIO (`http://127.0.0.1:9100`, `kame_apply` / `kame_apply_local_only`).

### Mail

| Variable | Value |
| --- | --- |
| `RESEND_API_KEY` | Resend API key (deployed environments) |
| `MAIL_FROM` | Verified sender, e.g. `Kame Apply <no-reply@example.com>` |
| `SMTP_HOST` / `SMTP_PORT` | Local only: Mailpit `127.0.0.1:1125` |

Without `RESEND_API_KEY`, the API uses SMTP; local Mailpit captures everything at `http://localhost:8125`.

### Auth and Google

| Variable | Value |
| --- | --- |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth web client. Authorized redirect URI: `https://api.example.com/api/v1/auth/google/callback` |
| `AUTH_RATE_LIMIT_ENABLED` | `true` (only E2E turns it off) |
| `ACCESS_TOKEN_TTL_SECONDS` / `REFRESH_TOKEN_TTL_SECONDS` | Defaults are fine |

Google is optional; the endpoints 404 without credentials.

### AI

Workspace AI keys are added in **Settings → AI** and encrypted with `MASTER_KEK`; no global provider key is required. `GEMINI_API_KEYS` / `GROQ_API_KEY` in `.env` are only for the opt-in live tests (`RUN_LIVE_AI=1`).

| Variable | Value |
| --- | --- |
| `AI_MAX_OUTPUT_TOKENS` | `1024` default |
| `DBOS_SYSTEM_DATABASE_URL` | Optional DBOS system database; defaults to `DATABASE_URL` when unset |

### Optional integrations

| Feature | Variables | Setup |
| --- | --- | --- |
| Web push | `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | `uv run python scripts/dev/generate-vapid-keys.py --out-dir /etc/kame-apply` |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET` | BotFather; webhook `https://api.example.com/api/v1/webhooks/telegram` |
| Inbound email alerts | `INBOUND_EMAIL_DOMAIN`, `INBOUND_WEBHOOK_SECRET` | Cloudflare Email Worker → `https://api.example.com/api/v1/webhooks/inbound-email` with `X-Kame-Signature: sha256=<hmac>` |
| Sentry | `SENTRY_DSN` (API), `NUXT_PUBLIC_SENTRY_DSN` (web) | Optional; PII stays off |
| Feedback to GitHub | `GITHUB_FEEDBACK_TOKEN`, `GITHUB_FEEDBACK_REPO` | Optional; without it feedback is audit-logged only |

Deployed environments fail closed on the inbound and Telegram webhooks when their secrets are missing. Prod refuses to start with the Telegram bot enabled and no `TELEGRAM_WEBHOOK_SECRET`.

## 3. Web environment (build time)

`deploy:web:dev|prod` runs `nuxt generate`, so these are read at build time:

| Variable | Value |
| --- | --- |
| `NUXT_PUBLIC_API_BASE` | `https://api.example.com` (must be set; the script refuses to build without it) |
| `NUXT_PUBLIC_EXTENSION_ID` | Chrome extension ID from `chrome://extensions` or the Web Store |
| `NUXT_PUBLIC_SENTRY_DSN` | Optional browser Sentry DSN |
| `NUXT_PUBLIC_ENABLE_DESIGN` | Leave unset; E2E sets `true` |

Publish target: Cloudflare Pages project. Set `CF_PAGES_PROJECT` and install `wrangler` to publish from the script, or upload `apps/web/.output/public` in the dashboard. Client routes fall back to the SPA shell through `apps/web/public/_redirects` (`/* /index.html 200`); prerendered `/` and `/legal/*` still win.

The extension handshake accepts `http://localhost:3100/*` and `https://*.kame.apply/*`. If the web app uses a different domain, add it to `externally_connectable` in `apps/extension/wxt.config.ts` and rebuild the extension.

## 4. Runner environment (`/etc/kame-apply/runner.env`)

| Variable | Value |
| --- | --- |
| `KAME_RUNNER_API_BASE` | `http://api:8100` inside Compose |
| `KAME_RUNNER_TOKEN` | Runner token created in **Settings → Runs** (shown once) |
| `KAME_RUNNER_WORKSPACE_ID` | Workspace id from **Settings → General** |
| `KAME_RUNNER_MODE` | `cloud` in Compose; `local` for a headed local runner |
| `KAME_RUNNER_HEADED` | `false` in Compose |
| `KAME_RUNNER_RUNNER_ID` | Unique runner name, e.g. `vm-1` |
| `KAME_RUNNER_MAX_CONCURRENCY` | Default `2` |

`deploy:runner:dev|prod` builds and ships the image; the runner starts only when a token and workspace id are present.

## 5. Deploy prerequisites

| Need | Details |
| --- | --- |
| Host | Linux VM with Docker + Compose, SSH access, at least 4 GB RAM (8 GB for the runner) |
| DNS | `api.example.com` → host IP; `app.example.com` → Cloudflare Pages |
| TLS | Caddy gets certificates automatically; `API_HOST` selects the hostname. Keep `KAME_COOKIE_SECURE=true` on HTTPS; set it to `false` only for an HTTP-only dev host. |
| SSH | `DEPLOY_HOST` as an SSH alias (`user@host` or a `~/.ssh/config` host) |
| Registry (optional) | `KAME_REGISTRY` to push images; otherwise the deploy script ships them over SSH |
| Health URL (optional) | `DEPLOY_HEALTH_URL=https://api.example.com/healthz` for the post-deploy check |
| Cloudflare | R2 bucket + token; Pages project + `wrangler` login |
| Resend | API key + verified sender domain |
| Google | OAuth client (optional) |

## 6. First dev deploy runbook

```bash
# 1. Host: install Docker, create /opt/kame-apply, copy infra/ (the deploy script rsyncs it).
# 2. Write /etc/kame-apply/api.env from apps/api/.env.example with the values above.
# 3. Point API_HOST and DNS at the host.
export DEPLOY_HOST=user@dev-host
export API_HOST=api.dev.example.com
export DEPLOY_HEALTH_URL=https://api.dev.example.com/healthz

# 4. Build and start the API, Caddy, and Postgres.
pnpm run deploy:api:dev

# 5. Run migrations inside the API container (the DB is not exposed publicly).
pnpm run migrate:host:dev

# 6. Build and publish the web app with the dev API URL.
export NUXT_PUBLIC_API_BASE=https://api.dev.example.com
export NUXT_PUBLIC_EXTENSION_ID=<extension-id>
export CF_PAGES_PROJECT=kame-apply-dev
pnpm run deploy:web:dev

# 7. Smoke check.
curl -fsS https://api.dev.example.com/healthz
curl -fsS https://api.dev.example.com/readyz
```

Then sign up, add an AI key in **Settings → AI**, create a Track, run discovery, and tailor a job. For the runner, create a runner token in **Settings → Runs**, put it and the workspace id in `/etc/kame-apply/runner.env`, and run `pnpm run deploy:runner:dev`.

`migrate:host:dev` uses `docker compose exec -T api uv run alembic upgrade head` over SSH; the API container reads `MIGRATION_DATABASE_URL` from `api.env`. For prod, use `migrate:host:prod` (unlock word required) and take a backup first.

## 7. What is already set locally

`apps/api/.env` currently has the local database URLs, `ENVIRONMENT=local`, logging, CORS, and the dev-only live-test AI keys. Local defaults in `app/core/config.py` cover MinIO, Mailpit, JWT, and the master key, so `pnpm run dev:docker && pnpm run dev` works without more setup. The keys not present locally are the optional integrations above (Resend, Google, R2, VAPID, Telegram, inbound email, Sentry, GitHub feedback).

## 8. Verification

- `pnpm run ci:quality` and `pnpm exec playwright test` locally.
- `GET /healthz` and `GET /readyz` on the host.
- Sign-up, email verification (Mailpit or Resend), AI key test, discovery run, tailor accept, and one runner run.
- Check `GET /api/v1/ops/dashboard` as an admin for source health and AI cost.
