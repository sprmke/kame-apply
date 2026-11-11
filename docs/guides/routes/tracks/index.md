# Route: `/tracks` (Searches)

**Page:** `apps/web/app/pages/tracks/index.vue` · **Layout:** `default` · **Access:** signed in · `data.read` / `data.write`

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| List | Done | API | Documented | Phase 4 |
| New search | Done | role text or example | Documented | Examples hidden behind Browse examples |

## Overview

Lists active searches for the workspace. The UI calls them **Searches**; the API and database keep `Track`. Create from a short role description or an example.

## User-facing knowledge

A search is a role you want. We check company boards and bring back matches. Duplicate or archive from the list; **View matches** opens the Jobs list for that search.

### Common user questions

- **Where do templates come from?** Curated starters across industries (ESCO/O*NET backed).
- **What happens when I archive?** The Track leaves the active list; data stays for history.

## Sections

### List

Rows show folder-tab color, name, summary, and **View matches**. Secondary actions: duplicate, archive.

### New Track

Lead with **What role are you looking for?** Name is optional. **Browse examples** reveals the curated starters. Create calls `POST /api/v1/tracks` (ensures a career profile first).

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks` | List active |
| `POST /api/v1/tracks` | Create |
| `GET /api/v1/tracks/templates` | Templates |
| `POST /api/v1/tracks/{id}/duplicate` | Duplicate |
| `POST /api/v1/tracks/{id}/archive` | Archive |

## Implementation map

`tracks/index.vue`, `useActiveProfile`, i18n `tracks.*`.
