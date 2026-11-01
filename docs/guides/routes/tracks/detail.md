# Route: `/tracks/:id`

**Page:** `apps/web/app/pages/tracks/[id]/index.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Criteria builder | Done | role signal | Documented | NL + chips + more filters |
| Preview | N/A | — | Documented | Placeholder until Phase 5 |

## Overview

Edit Track criteria via natural language (compile + optional apply), chips (must-skills, no agencies), or More filters (work mode, location, region, salary, keywords, companies). **Run now** starts discovery and lists matched jobs (rule-based until Phase 6).

## User-facing knowledge

Update from text shows a pencil diff; Apply writes it. Removing a must-skill chip saves immediately. Preview count waits for discovery.

### Common user questions

- **Why is preview empty?** Discovery (Phase 5) fills match counts.
- **Does Update save?** Update previews; Apply (or chip edits) saves.

## Sections

### NL box

`POST .../criteria/compile` with `apply: false|true`.

### Chips

Titles, must/nice skills, agencies toggle → `PUT .../criteria`.

### More filters

Work modes, location + radius, region preset, timezone overlap, visa, salary, keyword exprs, company include/exclude (comma-separated) → Save → `PUT .../criteria`.

## Loading / errors

Shows skeleton while the workspace is loading or the track query is pending. On fetch failure, shows the API error string (no blank main).

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}` | Detail + criteria |
| `POST /api/v1/tracks/{id}/criteria/compile` | NL compile |
| `PUT /api/v1/tracks/{id}/criteria` | Save structured |
| `POST /api/v1/tracks/{id}/discover` | Run discovery |
| `GET /api/v1/tracks/{id}/jobs` | Matched track jobs |

## Implementation map

`tracks/[id]/index.vue`, i18n `tracks.*`.
