# Configuration and deploy runbook

Everything needed to run Kame Apply locally, on a dev host, or in production. Secrets are never committed; this page lists variable names and where each value comes from.

Canonical deployment layout: [`deployment.md`](./deployment.md). Prod deploys and remote writes need `applywave` in the same message (`no-prod-deploy.mdc`).

Step-by-step first deploy with exact sites, pages, and commands: [`docs/guides/deploy-dev.md`](../guides/deploy-dev.md).

## 0. Services used, and what is not needed

| Service | Needed? | What for |
| --- | --- | --- |
| **Cloudflare Pages** | Optional | Hosts the static Nuxt web app. The free VM profile serves it from Caddy instead. |
| **Cloudflare R2** | Optional | Resumes, rendered files, screenshots, backups (S3 API). The free VM profile uses MinIO instead. |
| **One Linux VM** (Oracle Always Free or Hetzner) | For always-on | Runs the API, Postgres, Caddy, backup, and optionally the runner. Local mode needs no VM. |
| **Domain + DNS** | Optional | A purchased domain is not required. Use a free DuckDNS name, `sslip.io`, or a tunnel. |
| **Resend** | Optional | Verification, reset, notifications, digests. SMTP (Gmail, Brevo, Mailpit) is the free alternative. |
| **Google OAuth** | Optional | "Continue with Google". |
| **Cloudflare Email Routing + Worker** | Optional | Inbound job-alert emails. |
| **Telegram Bot** | Optional | Needs-you alerts and digests on Telegram. |
| **Sentry** | Optional | Error tracking for API and web. |
| **GitHub token** | Optional | In-app feedback becomes a GitHub issue. |
| **AI provider key** | Optional per workspace | Gemini, OpenAI, Anthropic, Groq, OpenRouter, or local Ollama. Added in the app, not env. |

**Not needed:** Vercel, Supabase, Redis, AWS, Firebase, Heroku, Neon, a separate worker server, or a separate DB server. The API, database, durable workflows (DBOS is a Python library backed by Postgres), scheduler, and runner all live on the one VM. When Cloudflare is used, it is only Pages + R2 (+ optional Email Routing); the free VM profile uses Caddy and MinIO instead. Neon is mentioned in the stack notes as an optional dev convenience, not a requirement.

## 0a. Free personal mode

The app runs with no paid services:

- **Local:** `pnpm run dev:docker` and `pnpm run dev`. Postgres, MinIO, and Mailpit are local. No VM, domain, Cloudflare, or Resend.
- **Always-on free VM:** Oracle Always Free A1, a free DuckDNS name, Caddy serving the web build and API on one hostname, MinIO for files, and Gmail or Brevo SMTP. No purchased domain, Cloudflare Pages, R2, or Resend.
- **AI:** free Gemini or Groq keys, or local Ollama. Added per workspace in **Settings → AI**.
- **Runner:** run it locally, or use the extension.

Full walkthrough: [`docs/guides/run-free.md`](../guides/run-free.md). The hosted steps below remain valid when you want Cloudflare Pages, R2, and Resend.

## 0b. Collect these before the first deploy

| Item | How to get or generate it | Where it goes |
| --- | --- | --- |
| **VM with Docker** | Create an Ubuntu 24.04 VM (Oracle Always Free A1 or Hetzner CAX11), add your SSH public key, open ports 22, 80, 443. Install Docker Engine + Compose plugin. | `DEPLOY_HOST` in your shell |
| **Domain + DNS (optional)** | Register a domain, or use free DuckDNS (`kame.duckdns.org`) and point it at the VM IP. For a purchased domain in Cloudflare DNS: `api.<domain>` A record to the VM IP, **DNS only** (grey cloud) so Caddy can get a certificate. `app.<domain>` is the Pages custom domain. | `API_HOST`, `WEB_BASE_URL`, `CORS_ORIGINS` |
| **Postgres owner password** | `python -c "import secrets;print(secrets.token_urlsafe(24))"` | `/opt/kame-apply/infra/.env` (`POSTGRES_PASSWORD`) and `MIGRATION_DATABASE_URL` |
| **Postgres app password** | Same command, a different value. | `DATABASE_URL` and `APP_DB_PASSWORD` for `db:roles:host:*` |
| **JWT secret** | `openssl rand -base64 48` | `JWT_SECRET` in `api.env` |
| **Master KEK** | `python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"` | `MASTER_KEK` in `api.env` |
| **Cloudflare R2 (optional)** | Dashboard → R2 → Create bucket (`kame-apply`). R2 → Manage API Tokens → Create token with Object Read & Write. Copy the access key, secret, and `https://<account-id>.r2.cloudflarestorage.com`. Or skip R2 and use MinIO on the VM. | `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` |
| **Cloudflare Pages (optional)** | Dashboard → Workers & Pages → Create → Pages. Create a project (e.g. `kame-apply-dev`). Install `wrangler` and run `wrangler login`, or create an API token with Pages edit. Or skip Pages and serve the build from Caddy. | `CF_PAGES_PROJECT`, `CLOUDFLARE_API_TOKEN` |
| **Resend (optional)** | resend.com → API Keys → Create. Domains → add and verify your sender domain (SPF/DKIM records). Or use Gmail/Brevo SMTP, or Mailpit locally. | `RESEND_API_KEY`, `MAIL_FROM`, `SMTP_*` |
| **Google OAuth (optional)** | Google Cloud Console → APIs & Services → Credentials → OAuth client ID (Web application). Authorized redirect URI: `https://api.<domain>/api/v1/auth/google/callback`; authorized origin: `https://app.<domain>`. | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| **VAPID (optional)** | `uv run python scripts/dev/generate-vapid-keys.py --out-dir /etc/kame-apply` | `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` |
| **Telegram (optional)** | BotFather → `/newbot` → copy the token. Set the webhook to `https://api.<domain>/api/v1/webhooks/telegram` with a secret token. | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET` |
| **Inbound email (optional)** | Cloudflare Email Routing → Email Workers. The worker signs the raw body with HMAC-SHA256 using your secret and posts it to `/api/v1/webhooks/inbound-email?token=<workspace token>`. | `INBOUND_EMAIL_DOMAIN`, `INBOUND_WEBHOOK_SECRET` |
| **Sentry (optional)** | sentry.io → Create project (FastAPI and Vue). Copy the DSNs. | `SENTRY_DSN`, `NUXT_PUBLIC_SENTRY_DSN` |
| **GitHub feedback (optional)** | GitHub → Settings → Developer settings → Fine-grained token with Issues: write on the repo. | `GITHUB_FEEDBACK_TOKEN`, `GITHUB_FEEDBACK_REPO` |
| **AI provider (optional)** | Gemini, Groq, OpenRouter, OpenAI, Anthropic, or local Ollama. Add the key in the app: Settings → AI. | Not an env var; stored encrypted per workspace |

Use URL-safe passwords (`token_urlsafe`) for database URLs so `+`, `/`, or `=` do not break the connection string.

## 1. Environments

| Environment | API | Web | Database | Purpose |
| --- | --- | --- | --- | --- |
| Local | `pnpm run dev:api` on `:8100` | `pnpm run dev:web` on `:3100` | Compose Postgres on `:5442` | Development and E2E, no external accounts |
| Free VM | Compose `api` + Caddy on a VM | Caddy static on the same VM | Compose Postgres on the same VM | Personal always-on, no domain or Cloudflare |
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

### Storage (MinIO, Cloudflare R2, or another S3)

| Variable | Value |
| --- | --- |
| `S3_ENDPOINT_URL` | Internal endpoint: `http://minio:9000` on the free VM; `https://<account-id>.r2.cloudflarestorage.com` for R2 |
| `S3_PUBLIC_ENDPOINT_URL` | Browser-facing endpoint for presigned URLs: `https://kame-s3.duckdns.org` on the free VM; leave unset for local or R2 |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | MinIO root credentials, or an R2 token with object read/write |
| `S3_BUCKET` | Bucket name, e.g. `kame-apply` |
| `S3_REGION` | `auto` |

Local dev uses MinIO (`http://127.0.0.1:9100`, `kame_apply` / `kame_apply_local_only`). The free VM profile runs MinIO in Compose and needs no Cloudflare account. R2 is optional. Presigned upload and download URLs use `S3_PUBLIC_ENDPOINT_URL`; server-side reads and writes use the internal `S3_ENDPOINT_URL`.

### Mail

| Variable | Value |
| --- | --- |
| `RESEND_API_KEY` | Optional. Leave empty to use SMTP. |
| `MAIL_FROM` | Verified sender or the SMTP account address |
| `SMTP_HOST` / `SMTP_PORT` | Mailpit `127.0.0.1:1125`; Gmail `smtp.gmail.com:587`; Brevo `smtp-relay.brevo.com:587` |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP login and app password; empty for Mailpit |
| `SMTP_STARTTLS` / `SMTP_SSL` | `true` for port 587 / `true` for port 465 |

Without `RESEND_API_KEY`, the API uses SMTP. Local Mailpit captures everything at `http://localhost:8125`. Gmail needs 2FA and an app password; `MAIL_FROM` must match the Gmail address.

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
| `NUXT_PUBLIC_API_BASE` | `https://api.example.com`, or `https://kame.duckdns.org` when Caddy serves web and API on one host |
| `NUXT_PUBLIC_EXTENSION_ID` | Chrome extension ID from `chrome://extensions` or the Web Store |
| `NUXT_PUBLIC_SENTRY_DSN` | Optional browser Sentry DSN |
| `NUXT_PUBLIC_ENABLE_DESIGN` | Leave unset; E2E sets `true` |

Publish target: Cloudflare Pages project. Set `CF_PAGES_PROJECT` and install `wrangler` to publish from the script, or upload `apps/web/.output/public` in the dashboard. Client routes fall back to the SPA shell through `apps/web/public/_redirects` (`/* /index.html 200`); prerendered `/` and `/legal/*` still win.

Free VM alternative: `pnpm run deploy:free` builds the web with `NUXT_PUBLIC_API_BASE=https://<duckdns-name>` and copies it to `/opt/kame-apply/infra/web`; `infra/caddy/Caddyfile.free` serves it and proxies `/api/*` to the API. No Cloudflare account is needed.

The extension handshake accepts `http://localhost:3100/*` and `https://*.kame.apply/*`. If the web app uses a different domain, add it to `externally_connectable` in `apps/extension/wxt.config.ts` and rebuild the extension.

## 4. Runner environment (`/etc/kame-apply/runner.env`)

| Variable | Value |
| --- | --- |
| `KAME_RUNNER_API_BASE` | `http://api:8100` inside Compose |
| `KAME_RUNNER_TOKEN` | Runner token created in **Settings → Integrations** (shown once) |
| `KAME_RUNNER_WORKSPACE_ID` | Workspace id from **Settings → General** |
| `KAME_RUNNER_MODE` | `cloud` in Compose; `local` for a headed local runner |
| `KAME_RUNNER_HEADED` | `false` in Compose |
| `KAME_RUNNER_RUNNER_ID` | Unique runner name, e.g. `vm-1` |
| `KAME_RUNNER_MAX_CONCURRENCY` | Default `2` |

`deploy:runner:dev|prod` builds and ships the image; the runner starts only when a token and workspace id are present.

## 5. Deploy prerequisites

| Need | Details |
| --- | --- |
| Host | Linux VM with Docker + Compose, SSH access, at least 4 GB RAM (8 GB for the runner). Oracle Always Free A1 is 2 OCPU / 12 GB. |
| DNS | Free VM: two DuckDNS names (app and S3) → host IP. Hosted: `api.example.com` → host IP; `app.example.com` → Cloudflare Pages. A purchased domain is optional. |
| TLS | Caddy gets certificates automatically; `API_HOST` selects the hostname. Keep `KAME_COOKIE_SECURE=true` on HTTPS; set it to `false` only for an HTTP-only dev host. |
| SSH | `DEPLOY_HOST` as an SSH alias (`user@host` or a `~/.ssh/config` host) |
| Registry (optional) | `KAME_REGISTRY` to push images; otherwise the deploy script ships them over SSH |
| Health URL (optional) | `DEPLOY_HEALTH_URL=https://api.example.com/healthz` for the post-deploy check |
| Cloudflare (optional) | R2 bucket + token; Pages project + `wrangler` login. The free VM profile uses MinIO and Caddy instead. |
| Resend (optional) | API key + verified sender domain. The free VM profile uses Gmail or Brevo SMTP. |
| Google | OAuth client (optional) |

## 6. First dev deploy runbook

```bash
# 1. Host: install Docker, create /opt/kame-apply, copy infra/ (the deploy script rsyncs it).
# 2. Write /opt/kame-apply/infra/.env with POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB,
#    and API_HOST. Write /etc/kame-apply/api.env from infra/kame-apply/api.env.example.
# 3. Point API_HOST and DNS at the host.
export DEPLOY_HOST=user@dev-host
export API_HOST=api.dev.example.com
export DEPLOY_HEALTH_URL=https://api.dev.example.com/healthz

# 4. Build and start the API, Caddy, and Postgres.
pnpm run deploy:api:dev

# 5. Create the RLS-restricted app role, then run migrations inside the API container.
#    APP_DB_PASSWORD must match the password in DATABASE_URL.
export APP_DB_PASSWORD=<same as api.env>
pnpm run db:roles:host:dev
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

For the free single-VM profile, replace steps 4 and 6 with `pnpm run deploy:free` (one DuckDNS hostname, Caddy web + API, MinIO, SMTP) and run the role/migrate steps with `COMPOSE_FILE=docker-compose.free.yml`. Full walkthrough: [`guides/run-free.md`](../guides/run-free.md).

Then sign up, add an AI key in **Settings → AI**, create a Track, run discovery, and tailor a job. For the runner, create a runner token in **Settings → Integrations**, put it and the workspace id in `/etc/kame-apply/runner.env`, and run `pnpm run deploy:runner:dev`.

`migrate:host:dev` uses `docker compose exec -T api uv run alembic upgrade head` over SSH; the API container reads `MIGRATION_DATABASE_URL` from `api.env`. For prod, use `migrate:host:prod` (unlock word required) and take a backup first.

## 7. What is already set locally

`apps/api/.env` currently has the local database URLs, `ENVIRONMENT=local`, logging, CORS, and the dev-only live-test AI keys. Local defaults in `app/core/config.py` cover MinIO, Mailpit, JWT, and the master key, so `pnpm run dev:docker && pnpm run dev` works without more setup. The keys not present locally are the optional integrations above (Resend, Google, R2, VAPID, Telegram, inbound email, Sentry, GitHub feedback).

## 8. Verification

- `pnpm run ci:quality` and `pnpm exec playwright test` locally.
- `GET /healthz` and `GET /readyz` on the host.
- Sign-up, email verification (Mailpit or Resend), AI key test, discovery run, tailor accept, and one runner run.
- Check `GET /api/v1/ops/dashboard` as an admin for source health and AI cost.
