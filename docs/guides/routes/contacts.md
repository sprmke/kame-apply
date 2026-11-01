# Route: `/contacts`

**Page:** `apps/web/app/pages/contacts.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| CSV import | — | name required per row | Documented | Phase 20e |
| List | — | — | Documented | |

## Overview

Import contacts (CSV-shaped text) used for referral matching on applications. The app never sends outreach; it only drafts text.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/contacts/import` | Bulk import |
| `GET /api/v1/contacts` | List |

## RBAC

`data.read` / `data.write`.
