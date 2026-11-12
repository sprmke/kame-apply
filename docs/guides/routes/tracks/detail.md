# Route: `/tracks/:id`

**Page:** `apps/web/app/pages/tracks/[id]/index.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Matches | Done | — | Documented | Top 10, View all, Open posting |
| Criteria builder | Done | role signal, facet keys/options | Documented | Pack-driven visible / More options / Show all |
| Preview | N/A | — | Documented | Placeholder until Phase 5 |

## Overview

Results first. **Run search** starts discovery with a live elapsed timer and a last-search line. **View matches** opens the full Jobs list. Each top match can be Shortlisted or Skipped inline. **More tools** holds Be Found, Gap plan, and Settings. The search settings (natural language, chips, field filters) sit below the match list. In deployed environments the run is queued and the page polls progress until it finishes; in local dev and tests it runs inline.

The filters come from the search's **field of work** (pack): a control can be visible, tucked under **More filters**, or hidden. **Show all filters** reveals hidden controls so nothing is unreachable. A hidden field that already has a saved value shows a **Set earlier** line and stays applied. Changing the field itself happens in Settings > General > Fields of work.

## User-facing knowledge

Update from text shows a pencil diff; Apply writes it. Removing a must-skill chip saves immediately. A Hospitality search shows kitchen groups (cuisine, kitchen type, station, covers per service), shifts, pay includes, and no timezone overlap. A Technology search shows stack, remote eligibility, and company filters instead. Empty fields mean "any".

### Common user questions

- **Why is preview empty?** Discovery (Phase 5) fills match counts.
- **Does Update save?** Update previews; Apply (or chip edits, or Save in the filters) writes.
- **Where did a filter go?** **More filters** holds secondary controls. **Show all filters** reveals the rest, including a saved value from another field.

## Sections

### Matches

Top 10 by score. **View all** opens `/jobs?track=:id`. **Open posting** goes to the source.

### NL box

`POST .../criteria/compile` with `apply: false|true`.

### Chips

Titles, must/nice skills, agencies toggle → `PUT .../criteria`.

### Field filters

Grouped by the pack: work mode, commute and radius, remote eligibility (when the field uses it), visa and relocation, salary and pay includes, shifts, employment types, posting age, facets, companies. **Save** writes all fields → `PUT .../criteria`. Facet keys and options are validated against the track's pack; an unknown key or option returns 422.

### Where we look

A disclosure below the filters shows the planned keyword + location queries and the providers for this field, with **Ready** or **Setup needed**. It calls `GET /tracks/{id}/where`. When the first run returns fewer than five matches and coverage is partial/thin, a notice says so and links to Settings > Alerts. Add a location first; the search planner does not invent places.

### More filters / Show all filters

Collapsed fields sit under **More filters** (keywords, languages, education, clearance, minimum score, companies when collapsed). Hidden fields appear only after **Show all filters**, with the **Set earlier** note when a value is already saved.

## Loading / errors

Shows skeleton while the workspace is loading or the track query is pending. On fetch failure, shows the API error string (no blank main).

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}` | Detail + criteria |
| `POST /api/v1/tracks/{id}/criteria/compile` | NL compile |
| `PUT /api/v1/tracks/{id}/criteria` | Save structured |
| `GET /api/v1/workspace/experience` | Field manifests (states, labels, facets) |
| `POST /api/v1/tracks/{id}/discover` | Run discovery |
| `GET /api/v1/tracks/{id}/jobs` | Matched track jobs |

## Implementation map

`tracks/[id]/index.vue`, `useExperience`, i18n `tracks.*`, `criteria.*`, `industry.*`, `rank.*`, `credential.*`.
