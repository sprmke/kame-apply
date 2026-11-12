# Route: `/tracks` (Searches)

**Page:** `apps/web/app/pages/tracks/index.vue` · **Layout:** `default` · **Access:** signed in · `data.read` / `data.write`

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| List | Done | API | Documented | Phase 4 |
| New search | Done | role text or example | Documented | Check settings previews roles, skills, filters; examples behind Browse examples |

## Overview

Lists active searches for the workspace. The UI calls them **Searches**; the API and database keep `Track`. Create from a short role description or an example.

## User-facing knowledge

A search is a role you want. We check company boards and bring back matches. Duplicate or archive from the list; **View matches** opens the Jobs list for that search.

### Common user questions

- **Where do templates come from?** Curated starters across industries (ESCO/O*NET backed).
- **What happens when I archive?** The Track leaves the active list; data stays for history.

## Sections

### List

Rows show folder-tab color, name, summary, field of work, and **View matches**. Secondary actions: duplicate, archive.

### New Track

Lead with **Field of work** (the workspace's enabled fields, primary selected), then **What role are you looking for?** Name is optional. Changing the field filters the examples, so a Hospitality workspace sees kitchen templates, not software ones, and sends `industry` with the new search. **Check settings** calls `POST /api/v1/tracks/plan` and shows a pencil preview: role titles, core skills, nice-to-have skills, work mode, employment type, freshness, and agency exclusion. Chips can be removed and the agencies toggle edited before saving; editing the description discards the preview.

**Create** uses the previewed criteria when one is open. Without a preview it sends `suggest: true`, so the API builds the same plan before insert (deterministic pack defaults when AI is not configured). A career profile is ensured first. **Browse examples** reveals the curated starters for that field plus General starters. If the field's pack is not enabled for the workspace, the API returns 422.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks` | List active |
| `POST /api/v1/tracks` | Create (`suggest: true` plans from the description; `industry` optional, defaults to the workspace primary) |
| `POST /api/v1/tracks/plan` | Preview a pack-aware plan without creating |
| `GET /api/v1/tracks/templates` | Templates (filtered client-side by enabled field) |
| `GET /api/v1/workspace/experience` | Enabled fields and resolved manifests |
| `POST /api/v1/tracks/{id}/duplicate` | Duplicate, carries the field |
| `POST /api/v1/tracks/{id}/archive` | Archive |

## Implementation map

`tracks/index.vue`, `useActiveProfile`, i18n `tracks.*`.

## UX clarity (2026-11-12)

- **New search** opens a sheet with three tabs: **Describe it**, **Pick a template**, **Copy a search**. Describe it is the default; the plan preview stays a pencil draft.
- Cards show name, the saved summary sentence, status (Active or Paused), and **How much we do** in user words.
- A new search gets a recommended schedule (every 4 hours, quiet 22:00 to 07:00, 12 new jobs a day) and the default **Find and prepare**.
- Empty state is one line plus **Start a search**.
- Actions no longer sit in a right-aligned overflow at 375. **View matches** and **Automation** keep one row; Duplicate and Archive wrap below.
