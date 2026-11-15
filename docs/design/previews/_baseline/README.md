# UX clarity baseline

**Captured:** 2026-11-12 · **Branch base:** `f413806` · **Tool:** `pnpm run capture:design-screenshots`

Raw captures live in `.audit-screenshots/harness/` (gitignored). This file records the verdict per route so the after comparison has something to beat.

Grades: **A** clear at first glance, **B** usable with a hesitation, **C** needs a doc or a guess, **D** broken or misleading.

| Route | Grade | Where am I | What is this for | Next action | Consequence | Waiting on me | Responsive | Main problem |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/` Today | B | pass | pass | pass | partial | pass | pass | "Needs you" items repeat; no "what happened since last visit"; list runs under the bottom bar |
| `/tracks` | B | partial | pass | pass | partial | n/a | pass | New search is a naked textarea; no template-first path; no summary sentence per search |
| `/tracks/:id` | C | fail | fail | partial | fail | n/a | partial | Three business sections with internal titles; "Suggest settings" has no consequence line; search fires immediately |
| `/tracks/:id/settings` | D | fail | fail | partial | fail | n/a | partial | Autonomy, sources, schedule, auto-submit jargon in one scroll; timezone typed by hand; no recommendation |
| `/tracks/:id/runs` | C | partial | partial | n/a | partial | n/a | pass | Technical run columns; failed runs do not say what to do |
| `/jobs` | B | pass | pass | pass | partial | n/a | partial | "Ineligible" label; context panel order buries why; hover-only explanations |
| `/applications` | B | pass | pass | pass | partial | n/a | pass | Statuses are fine; runner vocabulary leaks in the dossier |
| `/applications/:id` | C | partial | partial | partial | fail | partial | partial | Runner, replay, frozen at submit; approval actions do not state the consequence |
| `/profile` | B | pass | partial | pass | pass | n/a | pass | "Interview prep" names the wrong thing; completeness has no next three things |
| `/profile/answers` | B | pass | partial | pass | pass | n/a | pass | Quick setup adds blanks with no draft path; three names for the answer feature |
| `/studio` | D | fail | partial | partial | fail | n/a | fail | Empty until two selects are set; Critique, Diff, Insights, Skim, Parse; hardcoded English; mobile list crowds the document |
| `/responses` | D | fail | partial | fail | fail | n/a | pass | Asks for an application id; "Classify"; no match assist |
| `/contacts` | C | pass | pass | partial | partial | n/a | pass | Asks for a CSV header by hand |
| `/safety` | B | pass | pass | pass | pass | partial | pass | Reasons are internal strings |
| `/notifications` | C | partial | partial | pass | pass | partial | pass | Nav says Needs you, page says Notifications; event names are internal |
| `/coach` | C | fail | partial | partial | fail | n/a | pass | Nav says Practice, page says Candidates, feature is People I help |
| `/settings` | C | pass | partial | pass | pass | n/a | pass | One flat list mixing account, workspace, AI, connections, admin |
| `/settings/ai` | D | fail | partial | partial | fail | n/a | partial | Models by tier, Base URL, Bulk/Standard/Premium; the one thing a new user needs is not the hero |
| `/settings/integrations` | D | fail | fail | partial | fail | n/a | partial | Seven unrelated sections; MCP URL, leased, scopes, tokens |
| `/settings/sources` | C | partial | pass | n/a | partial | n/a | pass | Circuit open, latency, blocks shown as a user setting |
| `/login` `/register` | B | pass | pass | pass | pass | n/a | pass | Register does not say what happens next |

## Cross-cutting failures

1. **Internal words** in 11 routes. `check:ux-jargon` lists 25 strings.
2. **Two names for one thing:** Track/Search, Practice/People I help, answer bank/Answer help/Answer Desk, Needs you/Notifications.
3. **The user does the machine's work:** application id, CSV header, IANA timezone, model id, base URL, resume and search selection in Studio.
4. **No defaults:** schedule, quiet hours, cap, how-much-we-do, currency, notifications, answer bank, writing style.
5. **Mobile:** double page padding in several routes (layout and page both apply `px-4`), Studio's two-column layout, and action rows that wrap under the bottom bar.
6. **Copy policy:** bare section titles were the only legal option; a one-line intro was banned. Fixed in UX-0.

## What "after" must show

- Every route grade B or better, with no D.
- `pnpm run check:ux-jargon` clean.
- One primary action per view at 375, 820, and 1440.
- A cold account reaches its first reviewed match without a form field beyond the resume and one sentence.
