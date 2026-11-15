# Route: `/tracks/:id`

**Page:** `apps/web/app/pages/tracks/[id]/index.vue` · **Shell:** `apps/web/app/components/TrackShell.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Search header | Manual | — | Documented | Name, colour dot, status, More tools, field of work chip |
| Section tabs | Manual | — | Documented | Matches · What to look for · Automation · History · Improve, same order on every tab |
| Run status + actions | Done | — | Documented | Last search line, View matches, Find jobs now, live progress |
| Top matches | Done | — | Documented | Top 12 by score, risk seal, salary line, opens the Jobs reader |
| Coverage notice | Manual | — | Documented | Shown when the field has few results in the saved country |
| Where we look | Manual | — | Documented | Planned keyword + location queries and providers, `Ready` / `Setup needed` |

## Overview

**Matches** answers one question: what did this search find. It owns the run action, the run status line, the top matches, the coverage notice, and the **Where we look** disclosure. The full reader with triage lives at `/jobs?track=:id`. The criteria builder moved to `/tracks/:id/look-for`; this page links there through the section tabs.

All tabs share `TrackShell`, so the page name, status, More tools menu, and section order never move between tabs.

The field of work drives what appears on the tab: the chip names the pack, and the criteria page shows only the filters that fit that work. Changing the field happens in Settings > General > Fields of work.

## User-facing knowledge

A search is a role you want plus the rules that narrow it. **Find jobs now** checks the sources and fills the list. **View matches** opens every result for this search.

### Common user questions

- **Why so few jobs?** The coverage notice says when our sources are thin for this field and country, and offers a job alert instead of leaving an empty page.
- **Where do the results come from?** Open **Where we look** to see the exact search terms and providers, and whether each provider is ready or still needs setup.
- **Where do I change the filters?** **What to look for** holds the role brief, chips, and filters. Nothing is written until you accept a suggestion or save.
- **Why is a filter missing?** Some controls only apply to certain work. **Show every filter** on the criteria page keeps everything reachable.

## Sections

### Header

Colour dot, name, Active/Paused status, the field of work chip, and **More tools** (Be Found, Gap plan). Run search and the run status sit below the tabs.

### Run status

While running: a pulsing dot, elapsed seconds, and board/found/new/linked progress from `GET /api/v1/discovery/runs/{run_id}` polled every 2s. Otherwise: last search time plus the new-match count.

### Top matches

Up to 12 jobs ordered by score. Each row shows the score, title, company, work mode, salary when the posting states one, and a risk seal for caution or danger. Clicking opens `/jobs?track=:id&job=:jobId`.

### Coverage notice

When the first run returns fewer than five matches and `GET /api/v1/sources/coverage` reports partial or thin coverage for the field and country, one notice explains it and links to Settings > Alerts. Add a location on the criteria page first; the planner does not invent places.

### Where we look

A disclosure below the list shows the planned keyword + location queries and the providers for this field, each marked **Ready** or **Setup needed**. It calls `GET /api/v1/tracks/{id}/where`.

## Loading / errors

`TrackShell` shows a skeleton while the workspace or track query is pending and the API error string on failure, so no tab renders blank chrome.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}` | Detail + criteria |
| `GET /api/v1/workspace/experience` | Field manifests (states, labels, facets) |
| `GET /api/v1/sources/coverage` | Coverage level for a field and country |
| `GET /api/v1/tracks/{id}/where` | Planned queries and adapters |
| `POST /api/v1/tracks/{id}/discover` | Run discovery |
| `GET /api/v1/discovery/runs/{run_id}` | Live run progress |
| `GET /api/v1/tracks/{id}/runs` | Last-run line |
| `GET /api/v1/jobs?track_id=…` | Top matches list |

## Implementation map

`tracks/[id]/index.vue`, `components/TrackShell.vue`, `composables/useExperience`, i18n `tracks.*`, `industry.*`.

## UX clarity (2026-11-12)

- `/tracks/:id` is now **Matches**: last-run line, **Find jobs now**, a compact list of the top matches (score, salary, risk), and **View matches** for the full reader.
- The criteria page moved to `/tracks/:id/look-for`. Section tabs are **Matches**, **What to look for**, **Automation**, **History**, **Improve**. Old links to the criteria view land on Matches, which is the better default after a run.
- **Improve** replaces the hidden **More tools** disclosure and holds the gap plan (filled on first open) plus the Be Found link.
- The run action states its consequence through the live progress line ("14 sources, 9 new, 41 s").

## Industry packs (2026-11-13)

- The header chip names the field of work.
- The coverage notice and **Where we look** come from the pack's adapters, so a Hospitality search names its own boards rather than company ATS boards.
- Filters, shifts, pay includes, and facets live on `/tracks/:id/look-for` and follow the pack's visibility rules.
