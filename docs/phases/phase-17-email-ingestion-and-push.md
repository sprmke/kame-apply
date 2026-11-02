# Phase 17: Email alert ingestion, web push, Telegram

**Status:** Done (eng) · **Release:** R2 · **Depends on:** 14 · **Features:** F14 (alerts), F15 · **Reference:** [`research/02`](../research/02-job-discovery-and-site-access.md) §2 Layer 4 · [`architecture/email-ingest.md`](../architecture/email-ingest.md)

## Goal

Cover LinkedIn, JobStreet, Indeed, Glassdoor, and other gated boards through the alert emails they already send, and reach the user instantly on phone when something needs them.

## Acceptance scenarios

1. Settings shows the workspace's private forwarding address + per-provider setup guides (Gmail filter to auto-forward, Outlook rule).
2. A forwarded LinkedIn job-alert email creates jobs (title, company, location, link), resolves to the employer ATS when possible, and matches them to Tracks.
3. Unknown sender format → LLM fallback extraction; low confidence → "review imported jobs" item.
4. Web push (installed PWA) for Needs-you items; Telegram bot linked via one-time code delivers the digest and Needs-you alerts with deep links.
5. Forwarding-address abuse (spam) is rate-limited and filtered; the user can rotate the address.

## Tasks

- [x] Cloudflare Email Routing catch-all → Email Worker → signed webhook to API (raw MIME to R2).
- [x] Parsers: LinkedIn, JobStreet/SEEK, Indeed, Glassdoor, Kalibrr, Google Alerts, generic; link unwrapping (tracking redirects resolved safely server-side with SSRF protection).
- [x] Gmail-forward verification handling (forward confirmation emails surfaced to the user).
- [x] PWA (manifest, service worker, VAPID web push via `pywebpush`), notification permission UX at the right moment. Requires `VAPID_PRIVATE_KEY` (PEM contents) and `VAPID_PUBLIC_KEY`; without them push logs and sends nothing. Push and Telegram dispatch for Needs-you class events.
- [x] Telegram bot (webhook), link/unlink, message templates, deep links.
- [x] Optional personal/self-hosted mode: Gmail API listener (port kame-homes `gmail-listener`) behind a flag.

## Edge cases

HTML-only emails, truncated alerts, digest emails with 20+ jobs, non-English alerts, duplicate alerts, forwarded-as-attachment, sender spoofing (validate DKIM/SPF via headers Cloudflare passes; low trust otherwise).

## Testing

Parser fixtures (≥ 10 real anonymized emails per major sender); webhook signature tests; push/Telegram integration tests.

## Exit criteria

- [x] Scenarios 1–5 covered by parser fixtures + webhook/signature/rotate/Telegram/push/cross-tenant tests; docs updated; `pnpm run ci:quality` green.
