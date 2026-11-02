# Email alert ingest, web push, Telegram (Phase 17)

## Inbound address

Each workspace gets `alerts+{token}@{INBOUND_EMAIL_DOMAIN}` (Settings → Alerts). Rotate invalidates the old token.

Cloudflare Email Routing → Worker (`integrations/cloudflare-email-worker/worker.js`) →

`POST /api/v1/webhooks/inbound-email` with raw MIME, `X-Inbound-Token` / `?token=`, and `X-Kame-Signature: sha256=…` (HMAC of body with `INBOUND_WEBHOOK_SECRET`).

## Parsers

LinkedIn, Indeed, JobStreet/SEEK, Glassdoor, Kalibrr, Google Alerts, generic. Tracking URLs unwrapped without fetching private hosts. Low confidence → `needs_review` + Needs-you item. Gmail forwarding confirmations surface as Needs-you.

Jobs land as `source_key=email_alert` via the shared upsert path.

## Web push

PWA: `manifest.webmanifest` + `sw.js`. `POST /api/v1/push/subscriptions` stores endpoint keys. `notify_user` sends a real encrypted Web Push (`pywebpush`) when `VAPID_PRIVATE_KEY` (PEM contents) and `VAPID_PUBLIC_KEY` (base64url public key) are set; otherwise it logs and sends nothing. Endpoints are SSRF-checked. Needs-you class events (needs_review, risk_flag, run_failed, budget_reached) fan out to push and Telegram when those preferences are on.

Webhooks fail closed outside local/test: inbound email needs a valid HMAC and Telegram needs `TELEGRAM_WEBHOOK_SECRET` (prod refuses to start with the bot enabled and no secret).

## Telegram

`POST /api/v1/telegram/link` mints a one-time code. User opens `t.me/{bot}?start={code}`. Bot webhook `POST /api/v1/webhooks/telegram` completes the link. Unlink clears `chat_id`.
