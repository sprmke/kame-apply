# Route: `/answers`

**Page:** `apps/web/app/pages/answers.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Paste + draft | — | profile required | Documented | Phase 12 |
| Restricted items | — | — | Documented | fact notes |
| Tone / copy / bank | — | — | Documented | ⌘C / Tab |
| `?application=` | — | — | Documented | attaches session |

## Overview

Answer Desk: paste one or many form questions, get grounded drafts (or write-yourself boxes when AI is forbidden). Copy, tone controls, save to answer bank. Optional `?application=` links the session to an application dossier.

## User-facing knowledge

Restricted questions show profile notes only. Bank matches reuse your saved wording. ⌘C copies the focused draft; Tab moves between items.

## API reference

| Call | Purpose |
| --- | --- |
| `POST /api/v1/answer-desk/parse` | Split and draft |
| `POST /api/v1/answer-desk/items/{id}/tone` | Tone |
| `POST /api/v1/answer-desk/items/{id}/save-to-bank` | Save |
| `PATCH /api/v1/answer-desk/items/{id}` | Edit |

## RBAC

`data.write` for parse/tone/save; `data.read` for session reload.

## Implementation map

`apps/web/app/pages/answers.vue` · `apps/api/app/answers/`
