# Route: `/jobs`

**Page:** `apps/web/app/pages/jobs.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Board list | Done | query | Documented | Score column, one-line titles |
| Drawer / fit | Done | — | Documented | Phase 6 |
| Triage | Done | enum | Documented | Phase 6 |
| Risk seal | Done | — | Documented | Phase 7 |
| Skill highlights | Done | — | Documented | `match_terms` + inline marks |
| Score breakdown | Done | — | Documented | Collapsed `How the score is built` |
| Tailor | Done | — | Documented | Phase 9 → `/tailor/:id` |
| Mark applied | Done | — | Documented | Phase 11 → application row |

## Overview

Job research board: ranked matches, a formatted and collapsible posting, fit requirements with evidence, keyboard triage. The list is a three-column reader: match score, title, company and work mode. The posting is parsed into headings, paragraphs, lists, and tool chips by `JobDescription`; the first two sections show by default and **Read full description** reveals the rest. On mobile the list is a full page; selecting a job opens a full-screen document with a back action and a sticky Shortlist / Tailor / Open / Skip bar. Risk seals and reason quotes from Phase 7. Tailor opens the per-job workbench. **Mark applied** creates (or updates) an application and opens its dossier. Optional `?track=` scopes to one search.

Named skills in the posting are highlighted inline and summarized as chips above the description: **in your profile** (brand fill, check), **related** (pencil fill, half mark), and **not in profile** (neutral fill, minus). A **Highlight matches** checkbox turns inline marks off; the chips stay as a stack summary. The preference persists in `localStorage`. The context panel adds a collapsed **How the score is built** disclosure with one bar per `score_components` signal.

## User-facing knowledge

The list column has a `Match` / `Job` header so the leading number is self-explanatory. Every row is the same height: the score is right-aligned in a fixed 2.25rem column, the title is clamped to one line with the full text on hover, and company and work mode share a second line. Risk appears inline as `! Caution` or `✕ High risk`, and an ineligible job is marked in the same line, so no row carries chips or wrapping text. Sort by match (default), newest, or salary. Skip reasons train ranking for that search. Zero results show relaxation suggestions when a search is selected. The header keeps only **Include ineligible** and sort; CSV and the shortcut legend moved out of the primary controls. The right panel leads with the score and risk seal, then **Next**: **Tailor** is the one filled action, **Shortlist** and **Open** sit under it, and **Skip** and **Mark applied** close the block as text actions. Risk reasons show only on caution and high-risk jobs, so a clear seal never carries a warning quote. Fit checks come after the actions and are clamped to three lines with a **Show all checks** control.

Skills in the posting are summarized above the description, with a check for skills already in your profile, a half mark for related evidence, and a minus for skills we found no evidence for. Clicking nothing is required: the same terms are marked in the posting itself. **How the score is built** opens a short breakdown of the signals behind the number, in plain words such as Skills, Title, and Freshness.

## Sections

### Board list

- Header: `Match` over the score column, `Job` over the text column.
- Row: right-aligned tabular score, then a two-line text block. Title truncates on one line (`title` attribute carries the full text); the second line is company, work mode, and any status marker.
- Selected row: `bg-brand-50` with a 2px brand inset on the left edge; the score turns brand-700.
- Reason chips live in the right panel, not in the list, so repeated signals such as "Title match" do not repeat down the column.
- The column is `min-w-0` at every breakpoint: verify no horizontal scroll at 375px.

### Skill highlights

- Source: `match_terms` on `GET /track-jobs/{id}`; terms come from a curated named-skill vocabulary plus the user's profile skills. Verdicts compare against profile evidence and the qualification ledger.
- Chips group matches first, then related, then gaps. The legend under the chips reads `{n} in your profile`, `{n} related`, `{n} not in profile`; zero groups are hidden.
- Inline marks use `<mark>` with `box-decoration-break: clone`, so a term that wraps reads as one continuous fill. Matches use a brand fill, related a pencil fill, gaps a neutral gray fill. No underlines. The summary chips pair each verdict with a glyph and a word; the inline fill is the at-a-glance layer.
- Terms are matched case-insensitively by default; ambiguous names (`Go`, `React`, `REST`, `Excel`) are case-sensitive and a few have blocked trailing phrases (`Excel at`, `Go to`). The segmenter takes the longest surface form, so `React.js` is not colored as `React` plus `.js`, and never matches inside a longer word.
- The description text is untrusted. Only short vocabulary labels and profile skill names are rendered; posting sentences are never inserted as HTML.
- Tests: `apps/web/tests/job-highlights.test.ts` (segmentation), `apps/api/tests/test_highlights_unit.py` (vocabulary + verdicts).

### Score breakdown

- `How the score is built` is a native `<details>` in the context panel; collapsed by default so the primary **Tailor** action stays visible.
- Rows are `score_components` filtered to known signals, clamped 0 to 100, sorted by strength. Each row has a label, a tabular value, and a bar. The bar is decorative; the number carries the meaning for screen readers.
- Closing note: `Your search sets how much each one counts.` The values are signal strengths, not point contributions.

## Keyboard

`j`/`k` move, `s` shortlist, `x` skip, `t` tailor, `o` open original, `?` help.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/jobs` | List |
| `GET /api/v1/track-jobs/{id}` | Detail |
| `POST /api/v1/track-jobs/{id}/triage` | Shortlist / skip / … |
| `GET /api/v1/jobs/export.csv` | Export |
| `GET /api/v1/tracks/{id}/relaxations` | Suggestions |
| `POST /api/v1/applications/mark-applied` | Log applied + open dossier |

## RBAC

`data.read` for list/detail/export; `data.write` for triage.

## Implementation map

`apps/web/app/pages/jobs.vue`, `apps/web/app/components/JobDescription.vue`, `apps/web/app/components/HighlightedText.vue`, `apps/web/app/components/ScoreBreakdown.vue`, `apps/web/app/lib/job-description.ts`, `apps/web/app/lib/job-highlights.ts` · `apps/api/app/matching/`, `apps/api/app/taxonomy/skills.py`

## UX clarity (2026-11-12)

- Header: one line of intro, **Best fit** sort, status chips (All, New, Shortlisted, Applied), and **More filters** (has salary, remote, show jobs not open to you).
- **Not open to you** replaces Ineligible everywhere; the reason is on the label.
- Context panel order is **Why this match**, then **How you match**, then safety and actions.
- One primary action per job: **Tailor resume**. Shortlist, Open original, and Skip are secondary.
- Mobile keeps a sticky action bar (Shortlist, Tailor resume, Skip) above the bottom nav. The list gets bottom padding so the bar never covers the last row.
