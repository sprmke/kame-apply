# Route: `/settings/alerts`

**Page:** `apps/web/app/pages/settings/alerts.vue` · **Layout:** `default` · **Access:** signed in (address rotate: manager)

## Progress overview

| Section | Status |
| --- | --- |
| Forwarding address | Documented |
| Setup guides | Documented |
| Telegram link | Documented |
| Recent messages | Documented |

## Overview

Private forwarding address for job-alert emails, provider setup steps, Telegram bot link, recent inbound parse results. The page lede explains that this is where run alerts and reminders arrive.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/inbound/address` | Address |
| `POST /api/v1/inbound/address/rotate` | Rotate token |
| `GET /api/v1/inbound/guides` | Setup steps |
| `GET /api/v1/inbound/messages` | Recent |
| `POST /api/v1/telegram/link` | Mint code |
| `POST /api/v1/telegram/unlink` | Unlink |

## Implementation map

`apps/web/app/pages/settings/alerts.vue` · `apps/api/app/ingest/` · `docs/architecture/email-ingest.md`


## Niche hospitality alerts

The setup list includes a Culinary Agents / JobStreet / SEEK / hcareers step when the workspace's field is Hospitality. Kame offers prefilled public search links from `GET /sources/alerts/guide`; the person creates the alert and forwards it. No board is automated or signed in to.
