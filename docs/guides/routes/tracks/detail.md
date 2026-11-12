# Route: `/tracks/:id`

**Page:** `apps/web/app/pages/tracks/[id]/index.vue` · **Shell:** `apps/web/app/components/TrackShell.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Search header | Manual | — | Documented | Name, colour dot, status, More tools |
| Section tabs | Manual | — | Documented | Criteria · Automation · History, same order on all three pages |
| Run status + actions | Done | — | Documented | Last search line, View matches, Run search |
| Brief | Done | non-empty role text | Documented | Suggest settings, then Use these or Discard |
| What we match on | Done | — | Documented | Grouped chips; agencies toggle saves immediately |
| Filters | Done | API schema | Documented | Collapsed by default; active filters summarised as chips |

## Overview

The **Criteria** tab answers one question: what is this search looking for. It owns the run action, the role brief, the compiled criteria, and the fine-grained filters. Results are not listed here; **View matches** opens `/jobs?track=:id`, where triage (shortlist, skip, open posting) lives.

All three search tabs share `TrackShell`, so the page name, status, More tools menu, and section order never move between tabs.

## User-facing knowledge

A search is a role you want plus the rules that narrow it. Change the sentence and ask for suggestions; nothing is written until you accept them. A skill you remove from a chip saves immediately. Matches fill in after a run.

### Common user questions

- **Did my edit save?** Only after **Use these**. The panel lists exactly what will change.
- **Why no jobs on this page?** Matches have their own list. **View matches** opens it for this search.
- **Where did the old "Update" button go?** It is now **Suggest settings**, followed by **Use these**, so nothing is written before you see it.

## Sections

### Header

Colour dot, name, Active/Paused status, and **More tools** (Be Found, Gap plan). Run search and the run status sit below the tabs.

### Run status

While running: a pulsing dot, elapsed seconds, and board/found/new/linked progress from `GET /api/v1/discovery/runs/{run_id}` polled every 2s. Otherwise: last search time plus the new-match count, linking to History.

### Brief

`FnTextarea` inside `FnField`. **Suggest settings** is disabled while the text is empty or a suggestion is in flight. It calls `POST .../criteria/suggest` with `apply: false` and renders the returned diff in pencil inside a dashed panel, with **Use these** and **Discard**. An empty diff raises a "No changes." toast instead of an empty panel. While a suggestion is open, chip removal and the agencies toggle edit the suggested criteria rather than the saved ones, so the preview stays consistent; **Use these** then `PUT`s the previewed criteria.

### What we match on

Four labelled groups: Roles, Skills (removable), Nice to have (pencil), Rules. The Rules group holds the **No agencies** toggle, which is a dashed chip when off and a checked chip when on, so the control looks the same in both states. Removing a must-skill or toggling agencies `PUT`s the criteria immediately.

### Filters

Collapsed by default. The header shows how many filters are on; collapsed it lists the active ones as chips. Expanded it holds work mode, employment type, posted within, location, radius, region, timezone overlap, visa sponsorship, salary (min, currency, period), keyword include/exclude, and company include/exclude. **Save filters** writes the whole criteria object and keeps any open suggestion.

## Loading / errors

`TrackShell` shows a skeleton while the workspace or track query is pending and the API error string on failure, so no tab renders blank chrome.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}` | Detail + criteria |
| `POST /api/v1/tracks/{id}/criteria/suggest` | Suggest criteria from the brief (`apply: false` previews) |
| `PUT /api/v1/tracks/{id}/criteria` | Save structured criteria (accepted suggestions, chips, filters) |
| `POST /api/v1/tracks/{id}/discover` | Run discovery |
| `GET /api/v1/discovery/runs/{run_id}` | Live run progress |
| `GET /api/v1/tracks/{id}/runs` | Last-run line |

## Implementation map

`tracks/[id]/index.vue`, `components/TrackShell.vue`, i18n `tracks.*`.
