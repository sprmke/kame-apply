# Glossary: the words the app uses

**Status:** Current · **Last updated:** 2026-11-12 · **Owner:** design + web

One term, one meaning, everywhere: web, extension, emails, notifications, and help. Internal names stay in code and logs. The UI speaks the right-hand column.

## 1. Core words

| Internal | User-facing | What it means | Where it shows |
| --- | --- | --- | --- |
| Track | **Search** | A role you want. We look for matching jobs on a schedule. | Nav, searches list, jobs filters |
| Run | **Search run** | One pass over the sources for a search. | Search history, Today |
| Autonomy | **How much we do** | How far we go on each match before we stop for you. | Search automation |
| Discover | **Find only** | We find and score jobs. You do the rest. | How much we do |
| Prepare | **Find and prepare** | We also draft a resume and letter for jobs you shortlist. | How much we do (default) |
| Assist | **Fill forms for me** | We fill application forms. You review and click Submit. | How much we do |
| Auto-submit | **Apply for me** | We submit jobs that pass every check. Starts with practice runs. | How much we do |
| Dry run | **Practice run** | We show what we would have sent, without sending. | Auto-apply block |
| Score threshold | **Minimum match** | Only jobs scoring at least this high are considered. | Auto-apply block |
| Kill switch | **Pause auto-apply** | Stops every automatic submit right now. | Auto-apply block |
| ATS | **Company career site** | The system a company uses for job posts and applications. | Sources, studio |
| Source | **Where we look** | A job board or company career site we check. | Search automation, settings |
| Circuit open | **Paused by us** | We stopped checking this source after errors. | Source health |
| Daily cap | **New jobs per day** | The most new matches we add in one day. | Schedule |
| Quiet hours | **Quiet hours** | We do not search or notify between these times. | Schedule |
| Tier: bulk / standard / premium | **Quick tasks / Everyday tasks / Best quality** | What kind of AI work runs on which model. | AI settings (advanced) |
| Fit ledger | **How you match** | Each job requirement checked against your profile. | Job context, tailor |
| Critique | **Resume check** | Scores and the top fixes for your resume. | Studio |
| Diff | **Suggested edits** | Changes you can keep or drop. | Studio, tailor |
| Insights | **What employers ask for** | Skills that show up most in your search. | Studio |
| Skim view | **6-second view** | What a recruiter sees at a glance. | Studio |
| Parse view | **What hiring software reads** | The text an applicant system pulls from your file. | Studio |
| Runner | **Apply helper** | Fills forms in a browser we control. You watch and approve. | Applications, settings |
| Live view / take over / hand back | **Watch / Take control / Let it continue** | Who is driving the browser. | Apply helper |
| Snapshot | **Posting as you applied** | A saved copy of the job post at submit time. | Application dossier |
| MCP URL | **Connection link** | The address an outside app uses to reach this workspace. | Connections |
| Agent | **Connected app** | An outside app you allowed to use this workspace. | Connections |
| Scopes | **Permissions** | What a connected app may do. | Connections |
| Leased | **In progress** | A request a connected app has picked up. | Connections |
| Classify | **Read reply** | We read an employer reply and suggest a status. | Replies |
| Proposal | **Suggestion** | A change waiting for you to accept. | Replies, profile |
| Evidence: strong / weak | **Proof from your resume / Our guess** | Where a claim comes from. | Resume, job context |
| Ineligible | **Not open to you** | The posting says it does not hire from your location or status. | Jobs |
| Interview prep (profile) | **Strengthen your profile** | Questions that add proof to your profile. | Profile |
| Coach candidates | **People I help** | Other people you are helping apply. | Tools |
| Needs you | **Needs you** | Decisions waiting on you. | Shell, Today |
| Answer help / answer bank / answer desk | **Answers** (bank) and **Answer help** (drafting) | Two features, two names, never mixed. | Profile, Tools |

## 2. Writing rules

1. **Verb + object on buttons.** "Find jobs now", "Tailor resume", "Use these edits". Never "Run", "Submit", "Execute", "Classify".
2. **The button keeps its name.** "Publish" produces "Published". "Save search" produces "Search saved".
3. **Explain the number.** Every score, count, or status has a tap target that says why, in a sentence.
4. **Say the consequence before the click.** Automatic or irreversible actions carry one line: "Starts with 3 practice runs. Nothing is sent."
5. **Two levels only.** Essentials first, then **More options**. No third level.
6. **No unexplained acronyms.** If a term must appear (for example a provider name), define it on the line below in plain words.
7. **Use the same word in the extension.** The panel says Search, not Track.

## 3. Banned in user-facing strings

`Track` (meaning a search), `autonomy`, `dry run`, `kill switch`, `score threshold`, `ATS`, `circuit open`, `tier`, `bulk`/`premium` (for people), `MCP`, `lease`, `scope`, `token`, `payload`, `classify`, `parse` (as a verb for people), `latency`, `deps`, `repo`.

Allowed exceptions: legal pages; `/_design`; admin-only pages that define the term on the same screen; the word "token" only inside the Connect a computer flow after it is explained as a one-time code.

`pnpm run check:ux-jargon` enforces this list.

## 4. Adding a word

1. Add a row here: internal name, user word, one-line meaning, where it shows.
2. Add the key under `glossary.*` in `apps/web/i18n/locales/en.json` when the UI needs the definition inline.
3. Update the matching route guide in `docs/guides/routes/`.
4. Run `pnpm run check:ux-jargon` and `pnpm run test:web` (the catalog test checks key parity).
