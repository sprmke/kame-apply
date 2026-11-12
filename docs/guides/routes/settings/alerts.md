# Route: `/settings/alerts`

**Page:** `apps/web/app/pages/settings/alerts.vue` · **Layout:** `default` · **Access:** signed in (address card and rotation: manager)

## Progress overview

| Section | Status |
| --- | --- |
| Your address | Documented |
| New address (rotate) | Documented |
| Setup steps | Documented |
| Telegram link | Documented |
| Recent emails | Documented |

## Overview

Bring job alerts in from outside. The page gives the workspace a private forwarding address, explains how to forward from Gmail, Outlook, and LinkedIn, links Telegram, and lists what arrived. Everything lands as matches; nothing is sent from here.

## Sections

**Your address** (managers only). The address plus **Copy address** as the primary action. **Get a new address** opens a confirm dialog because emails to the old address stop working.

**Where to forward from.** One intro line, then the provider steps behind the **Setup steps** fold. The steps come from `GET /api/v1/inbound/guides`.

**Telegram.** **Connect Telegram** mints a one-time code; a linked account shows **Connected** and **Disconnect** plus **Open bot**.

**Recent emails.** Subject or sender, source, jobs added, state chip, and date. States: Added, Needs a look, Skipped, Reading. Empty: one line plus the next action. Error: retry.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/inbound/address` | Address |
| `POST /api/v1/inbound/address/rotate` | New address; old one stops |
| `GET /api/v1/inbound/guides` | Setup steps |
| `GET /api/v1/inbound/messages` | Recent messages |
| `POST /api/v1/telegram/link` | Mint link code |
| `POST /api/v1/telegram/unlink` | Unlink |

## Implementation map

`apps/web/app/pages/settings/alerts.vue` · `apps/api/app/ingest/` · `docs/architecture/email-ingest.md`
