# Usability audit: first-run job search

**Date:** 2026-11-11
**Scope:** signup, Today, profile upload, parse review, Tracks, Track detail, discovery, Jobs, Runs.
**Method:** running the app locally at 1200px and 375px, Playwright screenshots and snapshots, API logs, source review, and an independent `design-reviewer` pass. The 820px tablet capture is still pending.

## Verdict

The core goal is not working end to end.

The app can ingest jobs and run discovery. It found 227 jobs for a Customer Support Lead Track. But a new user cannot reliably turn a resume into a profile, the first-run guide lies about completion, a global nav item is a placeholder, the Track page dumps 50 rows, and job text rendered as escaped HTML until this audit fixed it.

This is not a visual identity problem. Field Notes is readable. The failures are in first-run flow, data quality, error states, and navigation.

## What works

- Signup, workspace creation, and session handling.
- Resume upload and text extraction.
- Track creation from a free-text role description.
- Background discovery across Greenhouse, Arbeitnow, Remotive, RemoteOK, Jobicy, Himalayas, and other sources.
- Job list and detail reader, risk seals, fit ledger shell, and application tracking.
- Design tokens, typography, focus states, and responsive shell.

## Findings

| # | Severity | Finding | Evidence | Status |
| --- | --- | --- | --- | --- |
| 1 | Blocking | Parse returns 409 `ai_not_configured` with only a transient toast. The parsed column keeps saying "Parse the document to review fields." | `profile/review/[documentId].vue`, API log 409 | Fixed and verified: persistent inline error with an **AI providers** link. |
| 2 | Blocking | The global **Runs** nav item opens "Not built yet. Arrives in phase 15." The real Runs page is per Track and was unreachable from the Track page. | `pages/runs.vue`, `lib/nav.ts` | Fixed: removed the global item, `/runs` redirects to `/tracks`, Track has a Runs tab. |
| 3 | High | Job descriptions and fit text rendered escaped HTML (`&lt;h3&gt;`, `&amp;`) and collapsed into one unreadable paragraph. | captured screenshot, `textutil.html_to_text` | Fixed and verified: unescape and block-aware extraction, backfill for existing rows, tests. |
| 4 | High | Title scoring gives 65/100 for one shared generic word. "Customer Support Lead" ranked Growth Marketing Lead, Field Marketing Lead, and Engineering Lead at 66 to 68. | `matching/rule_score.py`, `hard_filters.py` | Fixed and verified: generic title words are ignored, hard filter requires a meaningful title token, and a re-score put only customer/support/success roles in the top 10. |
| 5 | High | Onboarding checklist hardcodes `done: false` for profile, Track, and extension. It never marks progress and includes a non-core extension step. | `OnboardingChecklist.vue` | Fixed in code: profile and Track are derived from data; extension step removed. The checklist hides once the workspace has data, so it is not visible in the audit account. |
| 6 | High | Track page lists 50 jobs with the full apply URL as link text, no shortlist/skip, and no cap. | `tracks/[id]/index.vue` | Fixed and verified: top 10, "View all", "Open posting". Shortlist/skip still missing. |
| 7 | Medium | New Track shows a flat grid of 44 role templates before the user's own description. | captured screenshot | Fixed and verified: templates are behind "Browse role templates". |
| 8 | High | `Run now` shows only "Running" for about 80 seconds. The Track Runs tab says "No runs yet" during the run. | Run button and Runs tab screenshots | Open. Needs queued/running row, elapsed time, sources checked, and a run link. |
| 9 | High | The review URL is not refresh-safe. `/profile/review/<documentId>` resolves the active profile, so a refresh or a second profile returns "Document not found." | API 404 after refresh | Open. Put the profile id in the route or resolve the document across the user's profiles. |
| 10 | Medium | Today headline says "227 strong matches across 1 Tracks." It pluralizes Track incorrectly and calls every match strong. | `applications/home.py` | Fixed in code: "matches" and correct Track plural. |
| 11 | Medium | Activity shows raw event names: `workspace.created`, `discovery.run_completed`, `matching.score_track`, repeated `safety.job_assessed`. | captured screenshot | Open. Map events to plain job-search language or hide the feed on empty Today. |
| 12 | Medium | The rail has 11 icon-only items. Tooltips exist, but a new user cannot scan it. | `AppRail.vue`, `lib/nav.ts` | Partially fixed: Runs removed. Group advanced items under More or label the rail. |
| 13 | Medium | Empty states do not explain the next action. "No Tracks yet", "No matched jobs yet", and "No runs yet" sit without a next step. | Tracks, Track, Runs | Open. Each needs one short next action. |
| 14 | Medium | The fit ledger shows "not evidenced" for every must requirement when the profile is empty. That is technically true but reads as a broken product. | captured screenshot | Open. Show "Add resume facts to see fit evidence" with a profile link. |
| 15 | Low | The Track heading repeats the folder tab and appends a period: "Customer Support Lead." | Track detail | Open. Use the name once, or a real summary. |

## Mobile findings (375px)

- **Jobs Reader does not stack cleanly.** The list pane keeps an internal scroll and shows four rows; the document pane starts below it; the context panel is pushed under the fixed bottom bar. A user has to scroll two different regions to reach the fit ledger.
- **Job titles truncate in the list** ("Senior Customer Support Executive, 6 month FT..."). H6 says job titles never truncate.
- **The bottom bar covers the context panel** in the captured viewport. The shell needs enough bottom padding and a mobile action bar for Shortlist, Skip, and Open.
- **Today still shows raw activity names** (`discovery.run_completed`, `matching.score_track`, `safety.job_assessed`) and the activity list is cut by the bottom bar.
- **Track is readable on mobile**, but the header actions wrap onto three lines and the Track name is repeated with a period.

## Root causes

1. **Placeholders shipped as done.** Phase 15 is marked Done, but the global Runs page is a placeholder. The phase exit criteria did not include "every nav item resolves to a real screen."
2. **No first-run acceptance scenario in CI.** The flow was tested in pieces, not as "new account to first shortlist."
3. **Error states were toasts only.** A 409 on the first meaningful action is invisible after the toast disappears.
4. **Data quality was not checked against the rendered UI.** Escaped HTML and single-token title matches passed unit tests but failed the actual job list.
5. **Navigation grew by phase, not by user job.** Eleven icons include advanced surfaces before the core loop works.

## Repair plan

### Slice 1: make the first run diagnosable (this change)

- Inline AI-key error on Parse.
- Remove the global Runs dead end; add Track Runs.
- Derive onboarding progress and remove the extension step.
- Hide the template wall.
- Cap Track matches at 10 with a clear path to the full list.
- Unescape job text and backfill existing rows.
- Ignore generic title words in scoring.

### Slice 2: make discovery observable

- Create the discovery run row before the first source request, not after the run finishes.
- Show queued/running/failed in Track Runs and next to `Run now`.
- Show elapsed time and sources checked.
- On completion, replace the button with "View matches" and a count.
- Add a retry action for a failed run.

### Slice 3: make relevance trustworthy

- Re-score the audit Track and compare the top 10 by hand.
- Add a relevance eval: for a Customer Support Lead Track, the top 10 must not contain marketing, engineering, or supply-chain leads.
- Show why a job ranked where it did, using the proof mark and the score components.
- Fix the Today headline to say "matches" and pluralize Track correctly.

### Slice 4: reduce navigation and empty-state noise

- Group Studio, Answer Desk, Coach, Contacts, Safety, and Settings under a More menu, or label the rail.
- Replace raw activity event names with plain language.
- Add one next action to every empty state.
- Make the review route refresh-safe.
- Show a profile-evidence prompt in the fit ledger when the profile is empty.
- Give the mobile Jobs screen one scroll region: list first, then a full-screen document with a sticky action bar for Shortlist, Skip, and Open.
- Stop truncating job titles in list rows; allow two lines.
- Add bottom padding so the fixed bar never covers the fit ledger or the last row.

## Verified after fixes

- Parse now shows a persistent inline block: "Add an AI key to use this. AI providers" with a link to `/settings/ai`.
- Track shows the top 10 matches, a **View all** link, **Open posting** labels, and a **Runs** tab.
- Runs tab is reachable and lists the completed discovery runs.
- After the title and hard-filter fix, the top 10 for Customer Support Lead were all customer, support, or customer-success roles. Growth Marketing Lead, Field Marketing Lead, Engineering Lead, and Supply Chain Lead were removed.
- Job descriptions render as readable text with paragraph breaks, not escaped HTML.
- Tracks hides the 44-template grid behind **Browse role templates**.

## Verification

- `uv run pytest apps/api/tests/test_matching_unit.py apps/api/tests/test_textutil.py apps/api/tests/evals/test_ranking_eval.py` passes.
- `pnpm run type-check` passes.
- `pnpm run lint` passes with pre-existing Vue warnings only.
- Manual: Tracks template wall hidden; Track shows 10 rows, View all, Open posting, Runs tab; Parse shows an inline AI-key error; job text is readable.
- Pending: re-run discovery after the title fix and inspect the top 10; mobile 375/820 screenshots.

## What not to do

- Do not add nav items or new AI surfaces until one Track goes resume to shortlist end to end.
- Do not call every ingested job a "strong match."
- Do not replace the stack or the Field Notes identity.
- Do not treat a toast as an error state for a blocking action.
