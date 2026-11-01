# Route: `/tracks`

**Page:** `apps/web/app/pages/tracks/index.vue` · **Layout:** `default` · **Access:** signed in · `data.read` / `data.write`

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| List | Done | API | Documented | Phase 4 |
| New Track | Done | name or template | Documented | Templates + NL |

## Overview

Lists active Tracks for the workspace. Create from a template or a short name/description.

## User-facing knowledge

A Track is a role folder (criteria, later sources and schedule). Duplicate or archive from the list.

### Common user questions

- **Where do templates come from?** Curated starters across industries (ESCO/O*NET backed).
- **What happens when I archive?** The Track leaves the active list; data stays for history.

## Sections

### List

Rows show folder-tab color, name, summary. Actions: open, duplicate, archive.

### New Track

Optional name + description, or pick a template. Create calls `POST /api/v1/tracks` (ensures a career profile first).

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
