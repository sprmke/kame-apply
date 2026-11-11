# Route: `/tracks/:id`

**Page:** `apps/web/app/pages/tracks/[id]/index.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Matches | Done | — | Documented | Top 10, View all, Open posting |
| Criteria builder | Done | role signal | Documented | Below results; NL + chips + more filters |
| Preview | N/A | — | Documented | Placeholder until Phase 5 |

## Overview

Results first. **Run search** starts discovery; **View matches** opens the full Jobs list. **More tools** holds Be Found, Gap plan, and Settings. The search settings (natural language, chips, More filters) sit below the match list. In deployed environments the run is queued and the page polls progress until it finishes; in local dev and tests it runs inline.

## User-facing knowledge

Update from text shows a pencil diff; Apply writes it. Removing a must-skill chip saves immediately. **Update this to refine your matches** is the hint under the role field. Match counts fill after discovery.

### Common user questions

- **Why is preview empty?** Discovery (Phase 5) fills match counts.
- **Does Update save?** Update previews; Apply (or chip edits) saves.

## Sections

### Matches

Top 10 by score. **View all** opens `/jobs?track=:id`. **Open posting** goes to the source.

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
