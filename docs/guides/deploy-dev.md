# First dev deploy: step by step

This is the detailed version of the required checklist. Follow it in order. Every secret stays on the host; never paste a secret into chat or commit it.

Prod uses the same steps plus `applywave` in the same message for deploy/migrate.

## 0. Accounts you need

| Account | Free? | Why |
| --- | --- | --- |
| Oracle Cloud or Hetzner Cloud | Free tier or about €4 to €6/month | The VM that runs the API, Postgres, Caddy, backups |
| A domain registrar (Cloudflare, Namecheap, Porkbun, ...) | About $10/year | `api.<domain>` and `app.<domain>` |
| Cloudflare | Free | Pages (web) and R2 (files) |
| Resend | Free tier | Outbound email |
| Google Cloud (optional) | Free | Google sign-in |
| Sentry (optional) | Free | Error tracking |

No Vercel, Supabase, Redis, AWS, Firebase, Heroku, or Neon is needed.

## 1. Create the VM

### Option A: Oracle Cloud Always Free

1. Go to `cloud.oracle.com` and sign up or sign in.
2. Open the hamburger menu, then **Compute → Instances**.
3. Click **Create instance**.
4. Name it `kame-dev`.
5. Image: **Canonical Ubuntu 24.04**.
6. Shape: **Ampere → VM.Standard.A1.Flex**. Set **2 OCPUs** and **12 GB** memory (use 4/24 if your region still offers it).
7. Boot volume: 100 GB is fine.
8. Under **Add SSH keys**, choose **Upload public key** and paste the output of:
   ```bash
   ssh-keygen -t ed25519 -C "kame-dev" -f ~/.ssh/kame_dev
   cat ~/.ssh/kame_dev.pub
   ```
   Keep `~/.ssh/kame_dev` private.
9. Networking: create or pick a VCN with a public subnet. Assign a **public IPv4 address**.
10. Create the instance and wait for **Running**.
11. Open the instance details and copy the **Public IP address**.
12. Open the subnet's **Security List** (or NSG) and add ingress rules for TCP **22**, **80**, and **443** from `0.0.0.0/0`. Without 80/443, Caddy cannot get a certificate.

Oracle capacity can be unavailable in some regions. If so, use Hetzner.

### Option B: Hetzner Cloud

1. Go to `console.hetzner.cloud`, create a project.
2. Click **Add Server**.
3. Location: closest to you. Image: **Ubuntu 24.04**.
4. Type: **CAX11** (ARM, cheapest) or **CX22** (x86).
   - On an Apple Silicon Mac the API image builds for `linux/arm64`. Pick **CAX11** (ARM) to match it. If you pick **CX22** (x86), build with `DOCKER_DEFAULT_PLATFORM=linux/amd64` or the image will not run.
5. SSH keys: add the same `~/.ssh/kame_dev.pub`.
6. Networking: public IPv4 enabled.
7. Firewall: allow **22**, **80**, **443**.
8. Create the server and copy its public IP.

### Connect and install Docker

Add an SSH alias on your machine:

```bash
cat >> ~/.ssh/config <<'EOF'
Host kame-dev
  HostName <PUBLIC_IP>
  User ubuntu
  IdentityFile ~/.ssh/kame_dev
EOF
chmod 600 ~/.ssh/config
ssh kame-dev
```

If your provider's Ubuntu image logs in as `root`, change `User ubuntu` to `User root`.

On the VM:

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

Log out and back in, then check:

```bash
docker --version
docker compose version
sudo mkdir -p /opt/kame-apply
sudo chown $USER:$USER /opt/kame-apply
```

On your machine, `DEPLOY_HOST=kame-dev` (the SSH alias).

## 2. Domain and DNS

1. Buy a domain at any registrar.
2. If you want Cloudflare DNS, add the site in the Cloudflare dashboard and change the nameservers at the registrar to the two Cloudflare nameservers shown.
3. In **DNS → Records**, add:
   - Type **A**, name `api`, content **VM public IP**, proxy status **DNS only** (grey cloud). Caddy needs direct access to port 80/443 to issue a certificate. If you keep the orange cloud, use a Cloudflare origin certificate or Caddy DNS challenge instead.
   - Do **not** add an A record for `app` yet; Cloudflare Pages will add the custom domain later.
4. Verify:
   ```bash
   dig +short api.dev.example.com
   ```
   It must return the VM IP.
5. Choose the values:
   - `API_HOST=api.dev.example.com`
   - `WEB_BASE_URL=https://app.dev.example.com`
   - `API_BASE_URL=https://api.dev.example.com`
   - `CORS_ORIGINS=["https://app.dev.example.com"]`

## 3. Generate the secrets

Run these on your machine. Use a URL-safe generator for database passwords so `+`, `/`, and `=` do not break the connection URL.

```bash
# Owner and app database passwords (run twice)
python3 -c "import secrets; print(secrets.token_urlsafe(24))"

# JWT secret
openssl rand -base64 48

# Master KEK (must be exactly 32 bytes, base64)
python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
```

What each one is for:

| Value | Purpose | If lost |
| --- | --- | --- |
| Owner password | Postgres superuser, Alembic, backups | Reset it in Postgres and update both env files |
| App password | The RLS-restricted API role | Re-run `db:roles:host:dev` with a new value |
| `JWT_SECRET` | Signs access tokens | All users must sign in again |
| `MASTER_KEK` | Wraps per-workspace AI keys | Existing AI keys cannot be decrypted; re-enter them |

Keep `MASTER_KEK` backed up. Do not change it after users add AI keys unless you run `python -m app.ops.rewrap_keks` first.

## 4. Cloudflare R2 (file storage)

1. Go to `dash.cloudflare.com` and pick your account.
2. In the left sidebar open **R2**.
3. Click **Create bucket**. Name it `kame-apply-dev` (or `kame-apply`), leave the location automatic, create.
4. Open **R2 → Manage R2 API Tokens** (some accounts show it under **API → Manage API tokens**).
5. Click **Create API token**.
   - Name: `kame-dev-api`.
   - Permissions: **Object Read & Write**.
   - Scope: the bucket you just created.
   - Create, then copy:
     - **Access Key ID** → `S3_ACCESS_KEY`
     - **Secret Access Key** → `S3_SECRET_KEY`
     - **Endpoint** `https://<account-id>.r2.cloudflarestorage.com` → `S3_ENDPOINT_URL`
   - The secret is shown once. Store it in the env file immediately.
6. Set:
   ```env
   S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
   S3_ACCESS_KEY=<access key id>
   S3_SECRET_KEY=<secret access key>
   S3_BUCKET=kame-apply-dev
   S3_REGION=auto
   ```

R2 free tier includes 10 GB storage. The API checks the bucket on startup; the bucket must exist.

## 5. Cloudflare Pages (web app)

1. In the Cloudflare dashboard open **Workers & Pages**.
2. Click **Create → Pages**.
3. Choose **Upload assets** (the build runs on your machine) and name the project `kame-apply-dev`. You do not need to connect a Git repository.
4. Install and authenticate `wrangler` on your machine. The deploy script calls the `wrangler` binary, so a global install is required:
   ```bash
   npm install -g wrangler
   wrangler --version
   wrangler login
   ```
   Or create an API token at **My Profile → API Tokens → Create Token**, custom token with **Account → Cloudflare Pages → Edit** and **Account → Account Settings → Read**. Export it as `CLOUDFLARE_API_TOKEN`, and set `CLOUDFLARE_ACCOUNT_ID` from the dashboard URL or **Account Home**.
5. Set `CF_PAGES_PROJECT=kame-apply-dev`.
6. After the first deploy, open the Pages project → **Custom domains → Set up a custom domain** and enter `app.dev.example.com`. If DNS is on Cloudflare, the CNAME is added automatically; otherwise add a CNAME to `<project>.pages.dev`.

The build needs `NUXT_PUBLIC_API_BASE=https://api.dev.example.com` so the static app points at the dev API.

## 6. Resend (outbound email)

1. Go to `resend.com` and sign up or sign in.
2. Open **API Keys → Create API Key**.
   - Name: `kame-dev`.
   - Permission: **Sending access**.
   - Copy the key (`re_...`) → `RESEND_API_KEY`.
3. Open **Domains → Add Domain** and enter your domain (or a subdomain such as `mail.example.com`).
4. Add the DNS records Resend shows (MX, SPF, DKIM) at your DNS provider, then click **Verify**. Wait until the domain is verified.
5. Set `MAIL_FROM="Kame Apply <no-reply@example.com>"` using the verified domain.
6. For a quick test before domain verification, use `MAIL_FROM="Kame Apply <onboarding@resend.dev>"` and send only to the email address on your Resend account. Resend restricts the test sender to your own address.

Resend free tier is enough for dev. If you prefer SMTP, set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and leave `RESEND_API_KEY` empty.

## 7. Put the values on the host

Create two files on the VM. Both must be readable only by you and Docker.

### `/opt/kame-apply/infra/.env` (Compose variables)

```env
POSTGRES_USER=kame_apply
POSTGRES_PASSWORD=<owner password>
POSTGRES_DB=kame_apply
API_HOST=api.dev.example.com
```

```bash
sudo mkdir -p /opt/kame-apply/infra /etc/kame-apply
sudo chmod 700 /etc/kame-apply
sudo nano /opt/kame-apply/infra/.env
sudo chmod 600 /opt/kame-apply/infra/.env
```

### `/etc/kame-apply/api.env` (API variables)

Start from `infra/kame-apply/api.env.example` in the repo and fill:

```env
ENVIRONMENT=dev
LOG_LEVEL=INFO
LOG_JSON=true

DATABASE_URL=postgresql+asyncpg://kame_apply_app:<app password>@postgres:5432/kame_apply
MIGRATION_DATABASE_URL=postgresql+asyncpg://kame_apply:<owner password>@postgres:5432/kame_apply

API_BASE_URL=https://api.dev.example.com
WEB_BASE_URL=https://app.dev.example.com
CORS_ORIGINS=["https://app.dev.example.com"]

JWT_SECRET=<jwt secret>
MASTER_KEK=<master kek>
COOKIE_SECURE=true
AUTH_RATE_LIMIT_ENABLED=true

S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY=<access key id>
S3_SECRET_KEY=<secret access key>
S3_BUCKET=kame-apply-dev
S3_REGION=auto

RESEND_API_KEY=<resend key>
MAIL_FROM=Kame Apply <no-reply@example.com>

SCHEDULER_ENABLED=true
AUTO_SUBMIT_ENABLED=false
AGENT_BRIDGE_ENABLED=true
```

```bash
sudo nano /etc/kame-apply/api.env
sudo chmod 600 /etc/kame-apply/api.env
```

The `backup` container reads the same file, so `MIGRATION_DATABASE_URL` must be present. The `api` container uses `DATABASE_URL` as the app role.

## 8. Deploy

On your machine, from the repo root:

```bash
export DEPLOY_HOST=kame-dev
export API_HOST=api.dev.example.com

# Leave this unset for the very first run if DNS has not propagated yet.
# The script waits up to 60 seconds for this URL and exits 1 on failure.
export DEPLOY_HEALTH_URL=https://api.dev.example.com/healthz

pnpm run deploy:api:dev
```

This builds the API image, syncs `infra/` to `/opt/kame-apply/infra`, ships or pushes the image, and starts Postgres, the API, and Caddy (Postgres starts because the API depends on it). The API serves 500s for tenant requests until the app role and migrations exist, but `/healthz` stays up, so the deploy can finish.

Create the app role and migrate:

```bash
export APP_DB_PASSWORD=<same app password as DATABASE_URL>
# Only needed if you changed these in /opt/kame-apply/infra/.env:
export POSTGRES_USER=kame_apply
export POSTGRES_DB=kame_apply

pnpm run db:roles:host:dev
pnpm run migrate:host:dev
```

Start the backup loop as well. The API deploy starts only `api` and `caddy`:

```bash
ssh kame-dev "cd /opt/kame-apply/infra && docker compose -f docker-compose.prod.yml up -d backup"
```

Check:

```bash
curl -fsS https://api.dev.example.com/healthz
curl -fsS https://api.dev.example.com/readyz
ssh kame-dev "cd /opt/kame-apply/infra && docker compose -f docker-compose.prod.yml logs --tail=100 api"
ssh kame-dev "cd /opt/kame-apply/infra && docker compose -f docker-compose.prod.yml logs --tail=50 backup"
```

If the deploy script exited on the health check because DNS was not ready, re-run it now that `dig +short api.dev.example.com` returns the VM IP.

Deploy the web:

```bash
export NUXT_PUBLIC_API_BASE=https://api.dev.example.com
export CF_PAGES_PROJECT=kame-apply-dev
# If you used an API token instead of `wrangler login`:
# export CLOUDFLARE_API_TOKEN=...
# export CLOUDFLARE_ACCOUNT_ID=...

pnpm run deploy:web:dev
```

The script runs `pnpm --filter @kame/web run generate`, then `wrangler pages deploy`. If `wrangler` is not on `PATH`, it only builds and prints the output directory, so confirm you see the upload URL in the output.

Then add the Pages custom domain `app.dev.example.com` in the Cloudflare dashboard.

## 9. First-use check

1. Open `https://app.dev.example.com` and sign up.
2. Check the verification email in Resend (or the Mailpit UI locally).
3. Sign in, open **Settings → AI**, add a provider key, and click **Test**. Gemini, Groq, OpenRouter, OpenAI, Anthropic, or a local Ollama URL work.
4. Create a Track, run discovery, open a job, tailor it, keep or remove a change, and accept.
5. Open **Settings → Integrations** and create a runner token if you want cloud apply runs. Put it and the workspace id (from **Settings → General**) in `/etc/kame-apply/runner.env`, then `pnpm run deploy:runner:dev`.

## 10. Common failures

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Caddy cannot get a certificate | `api` DNS is proxied (orange cloud), or ports 80/443 are closed | Set DNS-only and open the ports |
| `exec format error` when the API starts | Image built for ARM on an x86 host (or the reverse) | Use an ARM host, or rebuild with `DOCKER_DEFAULT_PLATFORM=linux/amd64` |
| Tenant requests return 500 | `kame_apply_app` role missing or wrong password | Run `db:roles:host:dev` with `APP_DB_PASSWORD` matching `DATABASE_URL` |
| `/readyz` is 503 | Migrations not run | `pnpm run migrate:host:dev` |
| Login works but pages 404 on refresh | Pages `_redirects` missing | Rebuild and deploy; the file is in `apps/web/public/_redirects` |
| CORS error in the browser | `CORS_ORIGINS` missing the web origin | Add `https://app.dev.example.com` and restart the API |
| Email not delivered | Resend sender/domain not verified | Verify the domain or use the test sender to your own address |
| `MASTER_KEK` startup error | Not base64 or not 32 bytes | Regenerate with the command above |
| R2 upload fails | Wrong endpoint, key, or bucket | Recheck the R2 token and bucket name |
| `deploy:web:dev` prints "Built static site" but uploads nothing | `wrangler` is not on `PATH` | `npm install -g wrangler`, then run `wrangler login` |
| Extension cannot connect | Web domain not in `externally_connectable` | Add the origin in `apps/extension/wxt.config.ts` and rebuild |

## 11. What to send me

- `DEPLOY_HOST` (SSH alias) and whether the SSH key is available in this session.
- The two domain names.
- Confirmation that I may generate the four secrets and write the two env files on the host over SSH.
- Cloudflare R2 token and Pages token (or `wrangler login`), and the Resend key. Do not paste secrets in chat; I can read them from the host files or you can place them yourself.

Then I can run the deploy, migrations, web publish, and smoke tests and report the result.
