# Route: `/contacts`

**Page:** `apps/web/app/pages/contacts.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| CSV import | — | name required per row | Documented | Phase 20e |
| List | — | — | Documented | |

## Overview

Import contacts (CSV-shaped text) used for referral matching on applications. A short lede explains the purpose and the CSV shape. The app never sends outreach; it only drafts text.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/contacts/import` | Bulk import |
| `GET /api/v1/contacts` | List |

## RBAC

`data.read` / `data.write`.

## UX clarity (2026-11-12)

- One **Paste anything** box accepts an email signature, a LinkedIn profile, a vCard, or CSV with or without a header.
- A preview lists the parsed contacts before import; the parser runs in the browser, so no AI key is needed.
- The empty state is one line.


## AI read (2026-11-13)

**Read with AI** calls `POST /api/v1/contacts/parse`. The endpoint sanitizes the text, runs the same deterministic parser first, and only then asks a tool-less model for a cleaner layout. Any email the model returns must appear in the source text. Without AI the button still returns the local result and says so.
