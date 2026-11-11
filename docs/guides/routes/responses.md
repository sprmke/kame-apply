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
