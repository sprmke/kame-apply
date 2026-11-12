# Route: `/responses`

**Page:** `apps/web/app/pages/responses.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Proposals | — | accept/dismiss | Documented | Phase 20a |
| Paste classify | — | body required | Documented | optional application id |

## Overview

Inbox for recruiter reply classification and proposed status changes. A short lede explains that the user approves every suggested status change. Paste a message (optionally tied to an application id). Accept moves the application; dismiss keeps it.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/responses/proposals` | Pending proposals |
| `POST /api/v1/responses/proposals/{id}/decide` | Accept or dismiss |
| `POST /api/v1/responses/ingest` | Classify pasted reply |

## RBAC

`data.read` to list; `data.write` to ingest and decide.

## UX clarity (2026-11-12)

- No application id field. Paste the sender, subject, and body; the page matches the application by company, title, and sender domain, and shows the guess.
- A searchable application select is the fallback. **Read reply** does the classify call.
- Status suggestions show as plain from → to chips with the citation.


## Server match (2026-11-13)

The page calls `POST /api/v1/responses/match` after a short pause in typing. The server compares company, title, and sender domain across the workspace and returns the best application or `null`. The browser keeps a local fallback, so the suggestion still works offline.
