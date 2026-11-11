# Run Kame Apply for free

There are two free paths. Pick one:

| Goal | Path | What you need |
| --- | --- | --- |
| Use it on this computer | Local mode | Docker, pnpm, uv. No VM, domain, Cloudflare, or Resend. |
| Always-on and reachable from anywhere | Free single-VM mode | One Oracle Always Free VM, a free DuckDNS name, and a free SMTP account. |

The app does not need Supabase, Convex, Vercel, Cloudflare, or a purchased domain to run. Those are optional hosted conveniences, not product requirements.

## 1. Local mode

This is the recommended starting point. It is the same full app: Postgres, MinIO, Mailpit, the API, and the web UI.

```bash
pnpm install
uv sync --all-packages
pnpm run dev:docker
pnpm run dev
```

Open:

| Service | URL | Notes |
| --- | --- | --- |
| Web | `http://localhost:3100` | The app |
| API | `http://localhost:8100` | `/docs` in local mode |
| MinIO console | `http://localhost:9101` | `kame_apply` / `kame_apply_local_only` |
| Mailpit | `http://localhost:8125` | Verification and reset emails |

Local defaults are already free:

- Postgres and MinIO run in Docker.
- Mailpit captures email. No Resend or domain.
- JWT and `MASTER_KEK` use local dev values.
- AI is optional. Add a free Gemini or Groq key in **Settings → AI**, or point at a local Ollama.
- The runner can run on the same machine, or you can use the extension.

If a port is already in use by another project, stop that project or run Kame Apply on different ports. In this workspace, ports `3100` and `8100` were previously occupied by a different app.

Reset local data:

```bash
pnpm run stop:docker
pnpm run db:reset:local
pnpm run dev:docker
```

## 2. Free single-VM mode

This profile removes the paid and blocked pieces:

- No purchased domain. Use a free DuckDNS name.
- No Cloudflare Pages. Caddy serves the static web build and proxies the API on one hostname.
- No Cloudflare R2. MinIO stores files on the VM.
- No Resend. Use Gmail SMTP or Brevo SMTP.
- No cloud runner. Run the runner locally when you need it.

### 2.1 Get the VM

Oracle Always Free is the only free always-on VM with enough memory for this stack. The current Always Free Ampere allowance is **2 OCPUs and 12 GB RAM**. Create an Ubuntu 24.04 instance and allow ports 22, 80, and 443.

If Oracle signup fails, do not buy Hetzner just for this. Use local mode, or try the signup fixes in section 3.

### 2.2 Get a free DuckDNS name

1. Go to `duckdns.org` and sign in with GitHub, Google, or Reddit.
2. Create two subdomains, for example `kame` and `kame-s3`.
3. Set both to the VM public IP and click **update ip**.
4. Verify from your machine:
   ```bash
   dig +short kame.duckdns.org
   dig +short kame-s3.duckdns.org
   ```
   Both must return the VM public IP.

Use `kame.duckdns.org` for the app (`API_HOST`) and `kame-s3.duckdns.org` for browser file uploads (`S3_HOST`). DuckDNS is free. Caddy gets Let's Encrypt certificates through port 80 for both names.

If the VM public IP changes, update both DuckDNS names. Oracle public IPs are normally stable.

### 2.3 Install Docker on the VM

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and back in. Create the app directory:

```bash
sudo mkdir -p /opt/kame-apply/infra /etc/kame-apply
sudo chown -R $USER:$USER /opt/kame-apply
sudo chmod 700 /etc/kame-apply
```

### 2.4 Generate secrets

```bash
# Owner password
python3 -c "import secrets; print(secrets.token_urlsafe(24))"

# App password (different value)
python3 -c "import secrets; print(secrets.token_urlsafe(24))"

# JWT secret
openssl rand -base64 48

# Master KEK
python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"

# MinIO root credentials (different values)
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

### 2.5 Host files

`/opt/kame-apply/infra/.env`:

```env
POSTGRES_USER=kame_apply
POSTGRES_PASSWORD=<owner password>
POSTGRES_DB=kame_apply
API_HOST=kame.duckdns.org

# MinIO root credentials. Also used by the API and backup containers.
S3_ACCESS_KEY=<minio user>
S3_SECRET_KEY=<minio password>
```

```bash
sudo nano /opt/kame-apply/infra/.env
sudo chmod 600 /opt/kame-apply/infra/.env
```

`/etc/kame-apply/api.env`:

```env
ENVIRONMENT=dev
LOG_LEVEL=INFO
LOG_JSON=true

DATABASE_URL=postgresql+asyncpg://kame_apply_app:<app password>@postgres:5432/kame_apply
MIGRATION_DATABASE_URL=postgresql+asyncpg://kame_apply:<owner password>@postgres:5432/kame_apply

API_BASE_URL=https://kame.duckdns.org
WEB_BASE_URL=https://kame.duckdns.org
CORS_ORIGINS=["https://kame.duckdns.org"]

JWT_SECRET=<jwt secret>
MASTER_KEK=<master kek>
COOKIE_SECURE=true
AUTH_RATE_LIMIT_ENABLED=true

# MinIO on the Compose network, not R2.
S3_ENDPOINT_URL=http://minio:9000
# Browser-facing MinIO through Caddy. Presigned uploads and downloads use this.
S3_PUBLIC_ENDPOINT_URL=https://kame-s3.duckdns.org
S3_ACCESS_KEY=<minio user>
S3_SECRET_KEY=<minio password>
S3_BUCKET=kame-apply
S3_REGION=auto

# Free SMTP. Gmail example. Leave RESEND_API_KEY empty.
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=<gmail app password>
SMTP_STARTTLS=true
SMTP_SSL=false
MAIL_FROM=Kame Apply <you@gmail.com>

SCHEDULER_ENABLED=true
AUTO_SUBMIT_ENABLED=false
AGENT_BRIDGE_ENABLED=true
```

```bash
sudo nano /etc/kame-apply/api.env
sudo chmod 600 /etc/kame-apply/api.env
```

Gmail requires 2FA. Create an app password at `myaccount.google.com/apppasswords`. `MAIL_FROM` must be the same Gmail address. Gmail allows about 500 recipients per day, which is enough for a personal app.

Brevo is a free alternative: `SMTP_HOST=smtp-relay.brevo.com`, `SMTP_PORT=587`, `SMTP_USER=<login>`, `SMTP_PASSWORD=<SMTP key>`, `SMTP_STARTTLS=true`, and a verified sender in `MAIL_FROM`. The free plan allows 300 emails per day.

### 2.6 Deploy

From the repo root on your machine:

```bash
export DEPLOY_HOST=kame-dev
export API_HOST=kame.duckdns.org
export S3_HOST=kame-s3.duckdns.org

# Only after `dig +short kame.duckdns.org` returns the VM IP.
export DEPLOY_HEALTH_URL=https://kame.duckdns.org/healthz

pnpm run deploy:free
```

`deploy:free` builds the API image, ships it, builds the static web app against `https://kame.duckdns.org`, copies the web build to the VM, and starts:

- `caddy` (web + API on one hostname)
- `api`
- `postgres`
- `minio`
- `backup`

The second DuckDNS name (`kame-s3`) is only for browser file uploads and downloads. Caddy proxies it to MinIO so presigned URLs work outside the Compose network.

Backups go to MinIO on the same VM. That protects against a bad migration, not against losing the VM. Copy the MinIO `backups/` prefix somewhere else if you care about disk loss.

Then create the app role and migrate:

```bash
export COMPOSE_FILE=docker-compose.free.yml
export APP_DB_PASSWORD=<the app password in DATABASE_URL>
export POSTGRES_USER=kame_apply
export POSTGRES_DB=kame_apply

pnpm run db:roles:host:dev
pnpm run migrate:host:dev
```

Open `https://kame.duckdns.org`, sign up, and check the verification email. The first deploy may need a minute for Caddy to get a certificate.

### 2.7 First-use check

1. Sign up and verify the email.
2. **Settings → AI**, add a free Gemini or Groq key, click **Test**.
3. Create a Track, run discovery, open a job, tailor, accept a change.
4. If you want apply runs, run the runner on your machine, or use the extension.

If you use the browser extension with a DuckDNS name, add `https://kame.duckdns.org/*` to `externally_connectable` in `apps/extension/wxt.config.ts` and rebuild the extension. The default only accepts `https://*.kame.apply/*`.

## 3. Oracle signup fixes

Oracle is strict about new accounts. Common causes:

- A disposable email, a virtual phone number, or a name/address that does not match the card.
- A VPN, proxy, or unusual browser fingerprint.
- A card that does not support international verification.
- The region is out of Ampere capacity.

Try:

1. Use a real personal email, your real name, address, and phone.
2. Disable VPN and ad blockers. Use a normal browser window.
3. Use a card in your own name that supports international transactions.
4. Sign up for the region closest to you. For the Philippines, Singapore.
5. If the console says **Out of capacity**, retry later or try another availability domain. Do not create multiple accounts just to change regions.
6. If you are comfortable with a card on file, upgrading to Pay As You Go often makes A1 capacity available. Always Free resources remain free within the 2 OCPU / 12 GB limit, but watch the billing page.

If signup stays blocked, use local mode. It is the same app and costs nothing.

## 4. Paid and optional services

| Item | Needed for local? | Needed for free VM? | Free option |
| --- | --- | --- | --- |
| VM | No | Yes | Oracle Always Free A1 (2 OCPU / 12 GB) |
| Domain | No | No | DuckDNS, `sslip.io`, or a tunnel |
| Cloudflare Pages | No | No | Caddy serves the web build |
| Cloudflare R2 | No | No | MinIO on the VM |
| Resend | No | No | Gmail SMTP, Brevo, or Mailpit locally |
| Google OAuth | No | No | Email and password |
| Sentry | No | No | Skip it |
| Telegram | No | No | Optional free bot |
| Inbound email | No | No | Skip it, or paste jobs manually |
| AI provider | No | No | Gemini free tier, Groq free tier, OpenRouter free models, Ollama |
| Runner | No | No | Run it locally, or use the extension |

## 5. Why not Supabase or Convex

They do not remove the need for compute, and they do not run this app as it is.

| Option | What it replaces | What it does not replace |
| --- | --- | --- |
| Supabase free | Postgres, auth, storage | The Python FastAPI API, DBOS workflows, the Playwright runner, the scheduler. The free database pauses after inactivity and has a 500 MB limit. |
| Convex free | Database and TypeScript backend functions | The Python API, PydanticAI, DBOS, the runner. Moving to Convex is a full rewrite, not a simplification. |
| Vercel free | Static web | The API, database, workflows, runner. |

The current stack already runs free locally. The only paid or blocked part was the optional hosted deployment, and the free VM profile above removes the domain, Cloudflare, and Resend costs.

## 6. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `pnpm run dev` fails because port 3100 or 8100 is busy | Stop the other project, or change the port and `NUXT_PUBLIC_API_BASE`. |
| No verification email locally | Open Mailpit at `http://localhost:8125`. |
| Caddy cannot get a certificate | DuckDNS must return the VM IP, ports 80 and 443 must be open, and no proxy should sit in front. |
| API restarts on the free VM | Check `/etc/kame-apply/api.env`: MinIO credentials must match `infra/.env`, and the app role must exist. |
| `/readyz` returns 503 | Run `COMPOSE_FILE=docker-compose.free.yml pnpm run migrate:host:dev`. |
| Uploads fail | Check MinIO: `docker compose -f docker-compose.free.yml logs minio`. The API creates the bucket on startup. `S3_PUBLIC_ENDPOINT_URL` must be `https://kame-s3.duckdns.org`, and that name must resolve to the VM with a valid certificate. |
| SMTP fails | Check the app password, port 587, and `SMTP_STARTTLS=true`. Gmail requires 2FA. |
| Web loads but API calls fail | `NUXT_PUBLIC_API_BASE` and `CORS_ORIGINS` must both use `https://kame.duckdns.org`. Rebuild the web after changing them. |
