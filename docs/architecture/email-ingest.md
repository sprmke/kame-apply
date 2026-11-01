# Email alert ingest, web push, Telegram (Phase 17)

## Inbound address

Each workspace gets `alerts+{token}@{INBOUND_EMAIL_DOMAIN}` (Settings → Alerts). Rotate invalidates the old token.

Cloudflare Email Routing → Worker (`integrations/cloudflare-email-worker/worker.js`) →

`POST /api/v1/webhooks/inbound-email` with raw MIME, `X-Inbound-Token` / `?token=`, and `X-Kame-Signature: sha256=…` (HMAC of body with `INBOUND_WEBHOOK_SECRET`).

## Parsers

LinkedIn, Indeed, JobStreet/SEEK, Glassdoor, Kalibrr, Google Alerts, generic. Tracking URLs unwrapped without fetching private hosts. Low confidence → `needs_review` + Needs-you item. Gmail forwarding confirmations surface as Needs-you.

Jobs land as `source_key=email_alert` via the shared upsert path.

## Web push

PWA: `manifest.webmanifest` + `sw.js`. `POST /api/v1/push/subscriptions` stores endpoint keys. VAPID keys optional (`VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY`).

## Telegram

`POST /api/v1/telegram/link` mints a one-time code. User opens `t.me/{bot}?start={code}`. Bot webhook `POST /api/v1/webhooks/telegram` completes the link. Unlink clears `chat_id`.
