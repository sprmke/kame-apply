# UX clarity overhaul: plain, guided, AI-assisted

**Status:** Planned · **Created:** 2026-11-12 · **Type:** cross-cutting UX program (web app; extension copy where shared)

Related: [`docs/design/ux-blueprint.md`](../../design/ux-blueprint.md), [`docs/design/design-system.md`](../../design/design-system.md), [`docs/guides/routes/`](../../guides/routes/), `.agent/skills/minimal-ui-copy`, `.agent/skills/human-copy`, `.agent/skills/design-review`.

---

## 1. Goal

Make every page understandable at first glance and make every feature need as little work from the user as possible.

A first-time user who is not technical should be able to:

1. Know **where they are, what the page is for, and what to do next** without reading docs.
2. Finish setup (resume, first search, schedule, AI) mostly by **accepting good defaults or AI drafts**, not by filling forms.
3. Never meet an unexplained internal term (Track, ATS, MCP, tier, lease, token, parse, dry run, circuit, latency).
4. Always be able to undo or review what AI did before it counts (pencil, then ink).

### Success criteria (measurable)

| # | Criterion | How we check |
| --- | --- | --- |
| S1 | Sign-up to first reviewed match in under 5 minutes, with zero form fields typed except the resume and one sentence about the role | Scripted usability run (§10) |
| S2 | Every page passes the **first-glance test** (§3.1) | `ux-clarity-review` skill report per route |
| S3 | Zero banned jargon terms in user-visible strings | `pnpm run check:ux-jargon` in `ci:quality` |
| S4 | Every setting has a default, and every multi-field form has a template or an AI fill path | Defaults catalog (§7) ticked |
| S5 | Every AI assist produces a draft the user accepts, edits, or discards | Code review + existing truthful/pencil tests |
| S6 | No regressions to P1-P7, RLS, activity log, a11y (WCAG 2.2 AA) | `ci:quality`, `security-auditor`, a11y smoke |

### Non-goals

- No new visual identity. Signal stays (indigo, cool canvas, Manrope, Phosphor, Reka UI).
- No change to the API/DB name `Track`; only user-facing words change.
- No product-scope changes beyond the assists listed in §6.
- No in-app product tour overlay ("coach marks"). Guidance lives in the page itself.

---

## 2. What is wrong today (audit)

Audit done against the current `main` working tree (pages under `apps/web/app/pages`, copy in `apps/web/i18n/locales/en.json`).

### 2.1 Jargon leaks into the UI

| Where | What the user sees | Problem |
| --- | --- | --- |
| `pages/tracks/[id]/settings.vue` | "Autonomy", numbered options 1-4 | Internal concept name; numbers add nothing |
| same, auto-submit block | "Dry-runs left: 3 · Score threshold: 0.7", "Enable live", "Pause" | Three technical ideas in one line, no meaning |
| same, sources | Groups "Job boards", "Company ATS", count "4 of 12 on" | "ATS" is jargon; user cannot tell what turning one off does |
| same, schedule | Timezone as free text, "Daily cap", "Quiet start/end" | User must type an IANA timezone; "cap" of what? |
| `pages/settings/ai.vue` | "Models by tier", "Bulk / Standard / Premium", "Base URL" | User must understand model routing to use AI |
| `pages/settings/integrations.vue` | "MCP URL", "Agent inbox: 2 waiting · 1 leased", "Connected agents", "Scopes", "Feature routing", "Apply runner", "Create token" | Developer vocabulary across a 497-line page with 7 unrelated sections |
| `pages/settings/sources.vue` | "Circuit open", "Latency", "Blocks" | Ops metrics shown as a user setting |
| `pages/studio.vue` | Tabs Critique / Diff / Insights / Skim / Parse; "Pick a Track"; "Run Insights"; table head "Freq" | Five tool names, two hardcoded technical strings |
| `pages/tailor/[trackJobId].vue` | "Fit ledger" | Signal component name used as a label |
| `pages/applications/[id].vue` | "Runner", "Apply with runner", "Replay", "Frozen at submit", "Approve submit / Keep draft" | Engine vocabulary in the dossier |
| `pages/responses.vue` | Field "Application id", button "Classify", "Status proposals" | User must find and paste a UUID |
| `pages/contacts.vue` | Placeholder `name,email,company,title` | Asks the user to hand-write CSV |
| `pages/tracks/[id]/gaps.vue` | "No gap items. Suggest from track must-skills." | Internal field name |
| `pages/jobs.vue` | "Ineligible", "Include ineligible" | No reason shown in the label |

### 2.2 Inconsistent names for the same thing

- **Track vs Search:** nav says "Searches" but the UI still says "Pick a Track" (studio), "Track sections" (aria), "Already applied to this job on another Track", "Track, company, and title are required", "Track order list is out of date".
- **Practice vs Candidates:** nav item `coach` is labelled "Practice", but the page title is "Candidates" and the page is about people you help apply. Meanwhile "Interview prep" in the profile is actually the profile Q&A that fills gaps (`InterviewDrawer.vue`).
- **Answer help / Answer bank / Answer Desk:** three names for two features.
- **Needs you** appears as a nav item that goes to `/notifications`, whose page is "Notifications".

### 2.3 The user does the machine's work

- Pasting an application id to file a reply (`responses.vue`).
- Typing a timezone, a CSV header, a model id, a base URL.
- Picking a base resume and a search in Studio before anything shows.
- Writing every answer-bank answer by hand after "Quick setup" adds empty-ish defaults.
- Choosing schedule, quiet hours, and a daily cap with no recommendation.
- Choosing autonomy with no recommended option.

### 2.4 Structure problems

- **Search detail** splits into Criteria / Automation / History, while "Be Found" (LinkedIn) and "Gap plan" hide under a "More tools" disclosure inside the search header.
- **Settings** mixes personal, workspace, admin-only ops, and developer integrations in one flat list. Integrations alone holds Claude, agent inbox, agents, routing, extension, runner, and platform autofill.
- **AI settings** shows usage, keys, budget, and model tiers with equal weight; the one thing a new user needs ("connect AI") is not the hero.
- **Studio** opens on an empty state that asks for choices instead of opening on the user's resume with a critique.

### 2.5 The copy rule fights clarity

`minimal-ui-copy` says "Unless we say so or really needed, do not add any text", and the `FieldLabel help` tooltip it recommends does not exist (`packages/ui/src/FnField.vue` has `hint` only). The result: bare section titles ("Autonomy", "Sources", "Schedule") with no hint of what they do. This plan updates the rule (§4) rather than ignoring it.

---

## 3. Design principles for this program

### 3.1 The first-glance test (every page, every section)

A reviewer, or the `ux-clarity-review` skill, answers these from a screenshot alone:

1. **Where am I?** Title says the thing in user words.
2. **What is this for?** One short line (max ~12 words) or an obvious visual.
3. **What do I do next?** Exactly one primary action is visually dominant.
4. **What happens if I click it?** Buttons are verb + object ("Find jobs now", not "Run"). Risky or automated actions show a consequence line before they happen.
5. **Is anything waiting on me?** Needs-you items are visible without hunting.

Fail any one and the section fails.

### 3.2 Rules

1. **Plain words first.** Use the glossary (§5.1). Internal names stay in code.
2. **Default everything.** Every control starts on a sensible value with a "Recommended" mark where a choice matters.
3. **Show the result, not the knobs.** Each settings block ends with a summary sentence of what will happen ("Checks 14 sources every 4 hours, 7 am to 10 pm Manila time, up to 12 new jobs a day").
4. **Basic first, advanced folded.** Two levels at most: the essentials, then "More options".
5. **Three ways to fill anything:** pick a template, let AI draft it, or type it. In that order of prominence.
6. **AI drafts, the user decides.** Every AI fill lands as pencil with "Use this / Edit / Discard". Facts carry evidence refs (P1). Untrusted text stays data (P6).
7. **Works without AI.** Every AI assist has a non-AI fallback (template, rule-based default, or manual) so the app still works with no key (P7).
8. **One primary action per view.** Secondary actions go quiet or into a menu.
9. **Explain numbers.** A score, count, or status always has a tap target that says why.
10. **Same thing, same name, everywhere.** Web, extension, emails, notifications.

---

## 4. Copy policy change (needs your approval in UX-0)

Update `minimal-ui-copy` (skill + `.cursor/rules/ui-minimal-copy.mdc`) from "no text unless required" to **"clear and short"**:

| Allowed | Limit |
| --- | --- |
| One section intro line under a section title, when the title alone fails the first-glance test | ~12 words, plain, no marketing |
| Field help as a `?` tooltip (`FnField` `help` prop) | 1 sentence |
| Consequence/summary sentence at the end of a settings block | 1 sentence, generated from values |
| Empty state | 1 line + 1 action (+ optional template picker) |
| First-run hint for a pattern (keyboard shortcuts, swipe) | Dismissible, shown once per user |

Still banned: page subtitles that restate the title, paragraphs, marketing, AI tells, em dashes (`human-copy`).

---

## 5. Shared building blocks (build once in UX-1)

### 5.1 Glossary (single source of user words)

New `docs/design/glossary.md` + i18n namespace `glossary.*`. Each entry: internal term, user word, one-line definition, where used.

| Internal | User-facing | One-line definition |
| --- | --- | --- |
| Track | Search | A role you want. We look for matching jobs on a schedule. |
| Run | Search run | One pass over job sources for a search. |
| Autonomy | How much we do | How far we go on each match before we stop for you. |
| Discover / Prepare / Assist / Auto-submit | Find only / Find and prepare / Fill forms for me / Apply for me | (per option, see §8.4) |
| Dry run | Practice run | We show what we would have sent, without sending. |
| Score threshold | Minimum match | Only jobs scoring at least this high. |
| Kill switch | Pause auto-apply | Stops all automatic submits right away. |
| ATS | Company career site | The system a company uses for job posts and applications. |
| Source | Where we look | A job board or company career site we check. |
| Circuit open | Paused by us | We stopped checking this source after errors. |
| Daily cap | New jobs per day | The most new matches we add in one day. |
| Quiet hours | Quiet hours | We do not search or notify during these hours. |
| Tier (bulk/standard/premium) | Quick tasks / Everyday tasks / Best quality | What kind of AI work runs on which model. |
| Fit ledger | How you match | Each job requirement checked against your profile. |
| Critique | Resume check | Scores and the top fixes for your resume. |
| Diff | Suggested edits | Changes you can keep or drop. |
| Insights | What employers ask for | Skills that show up most in your search. |
| Skim view | 6-second view | What a recruiter sees at a glance. |
| Parse view | What hiring software reads | The text an applicant system pulls from your file. |
| Runner | Apply helper | Fills forms in a browser we control. You watch and approve. |
| Live view / Take over / Hand back | Watch / Take control / Let it continue | |
| Snapshot | Posting as you applied | A saved copy of the job post at submit time. |
| MCP URL / Agent / Scopes / Lease | Connection link / Connected app / Permissions / In progress | |
| Classify (reply) | Read reply | We read an employer reply and suggest a status. |
| Proposal | Suggestion | A change waiting for you to accept. |
| Evidence (strong/weak) | Proof from your resume / Our guess | |
| Ineligible | Not open to you | The job says it does not hire from your location or status. |

### 5.2 New or extended components (`packages/ui` unless noted)

| Component | Purpose |
| --- | --- |
| `FnField` `help` prop | `?` tooltip on the label (fixes the gap in §2.5) |
| `FnSectionCard` | Standard settings section: title, optional intro line, body, optional summary sentence, optional "More options" fold |
| `FnChoiceCards` | Radio cards with title, one-line effect, optional "Recommended" badge, optional consequence preview. Replaces autonomy radios, schedule presets, AI setup paths |
| `FnMoreOptions` | One consistent disclosure for advanced controls |
| `FnSummaryLine` | Renders a plain sentence from current values (schedules, criteria, notifications) |
| `FnTerm` | Dotted-underline word that shows its glossary definition on hover/tap |
| `FnEmptyState` | One line + one action + optional templates |
| `FnAssist` (web) | "Fill with AI" button + pencil result + Use / Edit / Discard; shows "Add AI to use this" inline when no key; shows a non-AI alternative |
| `FnTemplatePicker` (web) | Cards of templates with preview, used for searches, answers, schedules, resumes |
| `FnStepper` (web) | Linear multi-step shell for onboarding and Tailor |
| `useFirstRunHint` (web composable) | Show-once hints, stored per user (server, not localStorage, so it follows devices) |

All land on `/_design` with every state (empty, loading, error, disabled, dark).

---

## 6. Leveraging AI (with guardrails)

Every assist: pencil draft, evidence refs for facts, tool-less call with delimited untrusted input, budget-aware, non-AI fallback, eval added (`ai-evals`), activity log on accept.

| # | Assist | Page | Builds on | Non-AI fallback | Backend work |
| --- | --- | --- | --- | --- | --- |
| A1 | **Setup from resume**: one upload pre-fills profile, answer bank, first search (title, location, seniority, salary band from profile facts), and a recommended schedule | Onboarding | `profile_extract`, `/tracks/plan` | Paste text + rule-based field mapping; template search | New `POST /onboarding/plan` orchestrating existing services; returns a draft bundle |
| A2 | **Describe your search** box is the hero; chips show the compiled result as a pencil diff; inline suggestions ("Add Product Engineer, about 31 more jobs") | Search criteria | `criteria/compile`, `criteria/suggest` (exist) | Template picker | Surface only; maybe add impact counts to suggestions |
| A3 | **Draft my answers**: fills answer-bank defaults from profile facts (work authorization, notice, location, salary expectation from search), sensitive fields excluded | Profile > Answers | `answers/draft.py` | Quick-setup templates with blanks | Extend quick setup to draft values; PII guard |
| A4 | **Voice without samples**: offer "Use my resume summary" or pick a preset voice (Plain, Warm, Formal) | Profile > Voice | voice analyze | Preset voices | Presets in config |
| A5 | **Reply auto-match**: paste an email, we find the application by company/title/sender domain and suggest the status | Replies | `responses` classify | Searchable application picker (no ids) | Matching service over the workspace's applications |
| A6 | **Contacts from anything**: paste an email signature, LinkedIn text, or vCard; we draft contact rows | Contacts | new prompt | CSV upload with column mapping UI | New prompt + endpoint, P6 sanitizing |
| A7 | **Fix my resume**: Studio opens on the latest resume with a check already run; "Apply top fixes" makes one pencil diff | Studio | `resume_critique`, `resume_tailor_review` | Manual edits | Auto-run critique on first open (budget-aware) |
| A8 | **Recommended automation**: suggest schedule, minimum match, and how-much-we-do from search breadth, past volume, and AI budget | Search > Automation | run history, budget | Static recommended preset | Small rule-based service (no LLM needed) |
| A9 | **Explain this**: "Why this score?" / "Why flagged?" in plain sentences from existing reasons | Jobs, Safety, Tailor | existing reasons/proof marks | Show raw reasons list | Formatting only; no new LLM call |
| A10 | **Gap plan auto-suggest** on first open of skill gaps | Search > Improve | gaps service | Empty state with "Suggest" | Trigger on open if empty |

Help text and the glossary stay static (no LLM) to keep cost at zero (P7).

---

## 7. Defaults and templates catalog

| Setting | Default | Source | Change needed |
| --- | --- | --- | --- |
| Timezone | Browser timezone, searchable select | `Intl` | Replace free-text input |
| Currency | From profile location | `tracks/currency.py` | Preselect |
| Search criteria | From A1 or a template | 40+ seeded templates (`taxonomy/seed.py`) | Expand to cover non-tech roles evenly (nurse, VA, CSR, teacher, accountant, sales, logistics, hospitality) |
| How much we do | **Find and prepare** (recommended) | Product default | Change server default if it is Discover |
| Sources | All official APIs and feeds on; company career sites auto-added | Sources registry | No user decision needed at create |
| Schedule | Every 4 hours, quiet 22:00-07:00 local, 12 new jobs/day | `daily_cap=12` exists | Auto-create on first search |
| Minimum match (auto-apply) | 85 | Product default | Display as whole number |
| Practice runs before auto-apply | 3 | Existing | Explain in UI |
| Notifications | In-app: all. Email: daily digest, needs you, risk. Run failed: in-app only | Product default | Seed per user |
| AI budget | Suggested amount with "about N tailored resumes a month" estimate | Usage pricing | Estimate helper |
| AI routing | Auto from the first working key; tiers hidden under More options | Existing "Auto" | Hide tiers by default |
| Answer bank | 12 standard questions drafted from profile (A3) | `answers` quick setup | Draft values |
| Voice | "Plain and direct" preset until samples exist | New presets | Config |
| Avoided phrases | Starter list prefilled | Existing placeholder | Prefill real values |
| Resume template | Default template; page size A4 or Letter from location | Studio | Auto-select |
| Studio context | Latest confirmed resume + most active search | Data | Auto-select |

---

## 8. Page-by-page redesign

Each page: problems, new structure, defaults/AI, copy. All pages keep empty, loading, error, partial, and permission-limited states (blueprint §6) and are checked at 375 / 820 / 1440 in light and dark.

### 8.1 App shell and navigation

- Primary nav: **Today · Searches · Jobs · Applications · Profile**. Keep.
- "More tools" becomes **Tools**, each item with a one-line description in the expanded list and in the command bar: Resume studio, Answer help, Replies, Safety check, Contacts, People I help.
- Rename `coach` nav "Practice" to **People I help** (matches the page). Move it under Settings > Workspace if usage is low (decide with data from the dogfood log).
- Bottom of the rail: **Needs you** goes to a real Needs-you view (filter of notifications that need a decision), label and page title match.
- Add a **Help** entry in the profile menu: glossary, "Finish setup" (re-opens the onboarding checklist), keyboard shortcuts, send feedback.
- Command bar: add actions in user words ("Find jobs now", "Tailor resume for…", "Add AI key").

### 8.2 Onboarding (new guided flow, `/start`)

Replaces the scattered checklist links with one stepper. Each step has a recommended path and a skip.

```text
Step 1  Your resume        [Upload]  [Paste text]  [LinkedIn PDF]  · Start blank
Step 2  Check the basics   Name, current title, location, years, top skills
                           (low-confidence fields first, each with a source line)
Step 3  Quick answers      Work authorization · Notice period · Salary · Relocation
                           (drafted from step 2, edit or accept)
Step 4  Your first search  "Senior support lead, remote, Philippines"  ← prefilled
                           Live preview: about 240 jobs in the last 30 days
                           Template cards if they want to start elsewhere
Step 5  How we help        (o) Find and prepare  (Recommended)
                           ( ) Find only   ( ) Fill forms for me
                           Every 4 hours, quiet 10 pm to 7 am  [Change]
Step 6  Turn on AI         Recommended free option + 3-step guide, or "Continue without AI"
                           (shows what works without AI)
Finish  "Searching 14 sources now…" → land on Jobs for that search
```

- Order note: today resume parsing needs an AI key (`career.aiKeyNeeded`). In UX-3, check whether a non-AI parse path exists; if not, move "Turn on AI" before step 1 with the free path as the recommended one, or add a rule-based parse fallback. Decide in UX-3, record the decision in the phase notes.
- Today keeps the checklist until setup is complete, linking back into the stepper at the first unfinished step.

### 8.3 Today

- Keep: next step card, Needs you, top matches, searches, this week.
- Add: a one-line **what happened since your last visit** ("12 new matches, 2 replies, 1 application needs your approval").
- Every number links to its filtered list.
- "This week" numbers get labels in full words, not trailing lowercase fragments.
- Empty states per section with one action.

### 8.4 Searches

**List (`/tracks`)**: cards show name, plain summary sentence, last searched, new matches, status (Searching / Paused / Waiting for next run). Primary: **New search**. "New search" opens a sheet with three tabs in this order: **Describe it** (AI, A2), **Pick a template**, **Copy an existing search**.

**Detail**: tabs renamed and reorganized:

| Tab | Contains |
| --- | --- |
| **Matches** | The search's jobs (Reader). Default landing tab after a run. |
| **What to look for** | Describe box (hero) → compiled chips by group (Roles, Must-have skills, Nice to have, Location and work mode, Pay, Companies) → **More options** (radius, timezone overlap, visa, keywords, company include/exclude). Summary sentence + live preview count at the bottom. Zero results suggest which filter to relax. |
| **Automation** | Three `FnSectionCard`s: **How much we do**, **When we search**, **Where we look**. Each ends with a summary sentence. A8 recommendation chip at the top: "Recommended for this search: every 4 hours, Find and prepare [Use this]". |
| **History** | Runs as plain rows: "Today 8:00 · 14 sources · 9 new · 41 s". Failed runs explain the reason and the fix. |
| **Improve** | Skill gaps (A10) and LinkedIn tips (Be Found), moved out of the hidden "More tools". |

**How much we do** (`FnChoiceCards`):

| Option | Effect line | Badge |
| --- | --- | --- |
| Find only | We find and score jobs. You do the rest. | |
| Find and prepare | We also draft a tailored resume and letter for jobs you shortlist. | Recommended |
| Fill forms for me | We also fill application forms. You review and click Submit. | |
| Apply for me | We submit jobs that pass every check. Starts with 3 practice runs. | Advanced |

When "Apply for me" is chosen, the block shows: "Practice runs: 2 of 3 left. We show what we would have sent, without sending.", "Minimum match: 85", the practice-run results as readable rows, and **Pause auto-apply**. Platforms that never allow auto-submit (P3) are listed as "Always manual: LinkedIn, Indeed, JobStreet".

**When we search**: preset cards (Every 4 hours (Recommended), Twice a day, Once a day, Weekdays only), timezone select (auto), quiet hours, new jobs per day, each with `help` tooltips. Summary sentence. Skipped-run reasons in plain words.

**Where we look**: grouped by "Job sites" and "Company career sites", all on by default, each with a one-line description and a health dot (healthy / paused by us). Admin-only health metrics stay in Settings.

### 8.5 Jobs (Reader)

- List rows keep score, title, company, salary, posted, risk seal; "Not open to you" replaces "Ineligible", with the reason on hover/tap.
- Context panel order: **Why this match** (plain sentences, A9) → How you match (fit ledger) → Safety → Actions.
- Single primary action per job: **Tailor resume**. Secondary: Shortlist, Skip (with reason menu), Mark applied, Open original.
- First-run hint for keyboard shortcuts and swipe (once, dismissible).
- Filters bar: plain chips ("New", "Shortlisted", "Has salary", "Remote"), "More filters" for the rest.

### 8.6 Tailor

`FnStepper` with three steps, visible at all widths: **1 How you match** (before → after verdicts) → **2 Suggested edits** (keep/drop each; "Keep all safe edits") → **3 Check and attach** (preview, grade ring, cover letter). Footer stays: Accept and attach · Edit · Discard. Gaps section says what to do in one line each.

### 8.7 Resume studio

- Opens on the latest confirmed resume and most active search (A7), with the resume check already shown.
- Tabs: **Resume check · Suggested edits · What employers ask for · 6-second view · What hiring software reads**.
- "Apply top fixes" creates one pencil diff.
- Template and page size have defaults and a preview thumbnail.
- Remove hardcoded English strings ("Pick a Track", "Run Insights", "Freq", "Accept all"), move to i18n with glossary words.

### 8.8 Applications and dossier

- List: plain statuses, route line, filters as chips; "Log application" opens a sheet that can prefill from a pasted job URL.
- Dossier order: header (status, next step) → **Next step card** (follow-up due, approval needed, interview) → timeline → what you sent (resume, letter, answers) → posting as you applied → notes and reminders → tools (interview prep, referrals).
- Apply helper (runner) section uses the glossary: Watch, Take control, Let it continue, **Approve and submit** / **Keep as draft** with the consequence line for each.

### 8.9 Answer help

- Steps on the page: **Paste questions** → drafts appear in pencil per question → copy or save to answer bank.
- Each draft shows "From your answer bank" or "From your profile" with the source.
- "Write this yourself" boxes keep their reason line (P3/P4 legal flags).

### 8.10 Profile

- Tabs: **Profile · Answers · Writing style · Files**.
- Profile: completeness meter with the next three things to add; the profile Q&A drawer is renamed from "Interview prep" to **Strengthen your profile** ("Answer a few questions so we can show more proof").
- Answers: A3 drafts; search; group by topic.
- Writing style: A4 presets first, samples optional.
- Files: upload, review, merge with plain step names.

### 8.11 Replies

- Paste the email → we find the application (A5) and show "Looks like your Acme Support Lead application. Suggested status: Interview". Accept / Change application / Dismiss.
- No id field. Fallback is a searchable application picker.

### 8.12 Safety, Contacts, People I help, Notifications

- **Safety**: "Check a message or link" box first; flagged jobs below with plain reasons (A9) and Skip as default focus.
- **Contacts**: A6 paste-anything; CSV upload with a column-mapping preview instead of a header placeholder.
- **People I help**: title and nav match; empty state explains the use in one line.
- **Notifications**: event names in user words; settings show a recommended preset and a summary sentence.

### 8.13 Settings (re-grouped)

```text
Account        Profile · Sign-in and devices
Workspace      General · Members · People I help (if moved)
AI             Connect AI (hero) · Budget and usage · More options (models, routing, fallback)
Connections    Browser extension · Email and Telegram alerts · Claude · Apply helper
Notifications  What we send and where (preset + table)
Admin          Source health · System status · Activity      (owners/admins only)
Danger zone
```

- **AI page**: hero `FnChoiceCards`: "Use a free provider (Recommended)", "Use my own paid key", "Connect my Claude". Each opens a short guided form with the provider preselected. Usage and budget below. Tiers, base URL, and feature routing live under More options. Feature routing moves here from Integrations.
- **Integrations** splits into Connections sub-pages, each with status, one action, and a short checklist ("1 Install the extension, 2 Click Connect, 3 Open a job page").
- **Claude connection**: "Connection link" with copy, "Requests for your Claude: 2 waiting, 1 in progress", "Connected apps" with Permissions in plain words.
- **Apply helper tokens**: "Connect a computer" flow, token shown once with a plain warning.
- **Admin** pages keep metrics but rename columns and add a legend.

### 8.14 Auth and legal

Copy check only; no structural change. Register shows what happens next ("Next: add your resume").

### 8.15 Extension (shared words only)

Apply the glossary to extension side panel strings so web and extension say the same thing. Layout changes are out of scope here.

---

## 9. Agent skills and tooling to create (UX-0)

These make the work repeatable and let an agent check and preview each page.

### 9.1 Skill: `ux-clarity-review` (`.agent/skills/ux-clarity-review/SKILL.md`)

- **Purpose:** pass/fail review of a route against the first-glance test (§3.1), the glossary, the defaults catalog, the AI-assist pattern, and required states.
- **Loop:** capture screenshots (Playwright MCP or `pnpm run capture:design-screenshots`) at 375/820/1440 light/dark → run `check:ux-jargon` → answer the five first-glance questions per section from the screenshot alone → check defaults, templates, AI path, non-AI fallback → check empty/loading/error/permission states → report.
- **Report:** per section `pass / fail / partial`, max six issues ranked by user impact, each with Before / After / Why (rule ID from this plan or the glossary), plus the one fix that matters most. Same report discipline as `design-review`.
- Pairs with `design-review` (visual) rather than replacing it.

### 9.2 Skill: `ux-preview` (`.agent/skills/ux-preview/SKILL.md`)

- **Purpose:** preview a redesigned page before wiring it to the API.
- **How:** build the new layout as a dev-only route `pages/_preview/<slug>.vue` using fixture data and real Signal components (never ships in production builds; guarded like `/_design`). Capture before (real route) and after (preview route) screenshots at three widths into `docs/design/previews/<slug>/` (or `.audit-screenshots/previews/` if we do not want them committed; decide in UX-0). Write a short `README.md` there with the decisions.
- **Exit:** user approves the preview, then the slice implements it on the real route and deletes the preview.

### 9.3 Skill: `plain-language` (or fold into `human-copy`)

- Glossary lookup rules, button verb+object rule, summary sentence patterns, consequence lines. Recommendation: fold into `human-copy` to avoid a new skill; add a "Glossary" section linking `docs/design/glossary.md`.

### 9.4 Agent and command

- Subagent `ux-reviewer` (`.claude/agents/ux-reviewer.md`) that runs `ux-clarity-review` on a route or diff. Read-only plus screenshot tools.
- Command `/ka-ux-review <route|diff>` and `/ka-ux-preview <route>`.
- Register in `.claude/README.md`, `.agent/skills/README.md`, `.codex` (run `python3 .codex/sync.py`), then `pnpm run setup:ai-tooling` and `pnpm run check:ai-tooling-sync`.

### 9.5 Script: `scripts/dev/check-ux-jargon.sh` → `pnpm run check:ux-jargon`

- Scans `apps/web/i18n/locales/en.json`, Vue templates (hardcoded text), and extension locale files for banned user-facing terms from the glossary, with an allowlist (legal pages, `/_design`, admin-only pages where the term is defined on the page).
- Also flags hardcoded English text in `<template>` that bypasses i18n.
- Added to `ci:quality` once UX-2 clears the backlog (warn-only before that).

### 9.6 Baseline capture

Before any UI change, capture every route at 375/820/1440 light/dark as the "before" set and run `ux-clarity-review` on each, producing a scored backlog in `docs/design/previews/_baseline/README.md`.

---

## 10. Delivery plan (slices)

Each slice is one branch and PR (`ux/NN-<slug>`), follows the repo build loop (`/ka-start-work` scratchpad, test first where practical, docs in the same change, `/ka-check-before-pr`). UI slices get `ux-reviewer` and `design-reviewer` passes.

| Slice | Scope | Exit criteria |
| --- | --- | --- |
| **UX-0 Foundations** | §4 copy policy update (needs approval), glossary, `ux-clarity-review`, `ux-preview`, `ux-reviewer`, commands, `check:ux-jargon` (warn-only), baseline capture | Skills synced (`check:ai-tooling-sync` green); baseline report with a score per route |
| **UX-1 Components** | §5.2 components on `/_design`, i18n glossary namespace | Every component in every state on `/_design`, unit tests, a11y smoke green |
| **UX-2 Shell, names, settings IA** | §8.1, Track→Search sweep, Practice→People I help, Needs you, Help menu, Settings regroup (§8.13 structure only) | `check:ux-jargon` zero for shell and nav; no route 404s; redirects for moved settings paths |
| **UX-3 Guided onboarding + defaults** | §8.2 stepper, A1, defaults from §7 that onboarding needs (schedule, notifications, how-much-we-do, timezone, currency) | S1 met in the scripted run; works with no AI key; evals for A1 |
| **UX-4 Searches** | §8.4 list, new-search sheet, detail tabs, criteria, automation, A2, A8, A10 | Each tab passes first-glance; summary sentences match saved values (tests) |
| **UX-5 Jobs, Tailor, Studio** | §8.5-8.7, A7, A9 | Studio opens with content for a seeded user; Tailor stepper at 375 |
| **UX-6 Applications, Answers, Profile, Replies** | §8.8-8.11, A3, A4, A5 | No id fields anywhere; A3/A5 evals; PII guard tests for A3 |
| **UX-7 Settings content, Safety, Contacts, Notifications** | §8.12-8.13 content, AI hero, Connections split, A6 | AI connect done in under 2 minutes in the scripted run; A6 eval with injection fixtures |
| **UX-8 Close-out** | Turn `check:ux-jargon` to blocking, full `ux-clarity-review` pass on every route, usability run, docs | All routes pass; S1-S6 met; status recorded |

Suggested preview gates: run `ux-preview` and get your approval before implementing UX-3, UX-4, and UX-7 (the three biggest layout changes).

### Scripted usability run (UX-3 and UX-8)

Five tasks on a fresh account, timed, with notes on every hesitation:

1. Sign up and get to your first matches.
2. Make the search only show remote jobs that pay at least a given amount.
3. Tailor your resume for the top match and attach it.
4. File an employer reply you got by email.
5. Turn on AI using a free provider.

Pass: each task done without docs, with no question about what a word means.

---

## 11. Backend and data changes (summary)

| Change | Slice | Notes |
| --- | --- | --- |
| `POST /onboarding/plan` (draft bundle from resume) | UX-3 | Orchestrates existing services; no new tables; activity log on accept |
| Server defaults on search create (schedule, how-much-we-do) | UX-3 | Activity log `track.schedule_created` etc. on auto-create |
| Per-user notification defaults seeding | UX-3 | Migration or service-side default |
| First-run hints store (`user_hint_dismissals` or a JSON column on user prefs) | UX-1 | Tenant scoping review; user-scoped, not workspace data |
| Answer-bank drafted values | UX-6 | PII guard, evidence refs |
| Reply auto-match service | UX-6 | Workspace-scoped query; untrusted email as data |
| Contacts parse prompt + endpoint | UX-7 | P6 sanitizing; draft only |
| Automation recommendation service (rules) | UX-4 | No LLM |
| Voice presets | UX-6 | Config |

Every new mutation gets an `activity_log` event; every new tenant table gets RLS and a cross-tenant test; every new prompt gets an eval. Regenerate the API client (`pnpm run gen:api-client`).

---

## 12. Docs to update (per slice)

- `docs/design/ux-blueprint.md`: IA (§2), key screens (§3), flows (§5) to match the new structure.
- `docs/design/design-system.md`: new components.
- `docs/design/glossary.md`: new, canonical user words.
- `docs/guides/routes/*`: every changed route (`route-guides` skill).
- `docs/architecture/*`: new endpoints and defaults.
- `.agent/skills/minimal-ui-copy`, `.cursor/rules/ui-minimal-copy.mdc`, `human-copy`: policy update.
- `AGENTS.md`: mention `ux-clarity-review` and `check:ux-jargon` if agents need them by default.

---

## 13. Risks and open decisions

| # | Item | Proposal |
| --- | --- | --- |
| D1 | Loosening `minimal-ui-copy` | Approve §4 limits in UX-0. Without it, most "what is this for" fixes are blocked. |
| D2 | Resume parsing needs AI today | Decide in UX-3: AI step first with a free provider, or a rule-based parse fallback. |
| D3 | Where "People I help" lives | Keep in Tools until dogfood data says otherwise. |
| D4 | Commit preview screenshots or not | Commit only approved after-shots under `docs/design/previews/`; keep raw captures gitignored. |
| D5 | Default "how much we do" = Find and prepare | Costs AI budget on shortlisted jobs only; confirm. |
| R1 | AI assists raise spend | Every assist shows cost class, respects budget, and has a non-AI path. |
| R2 | More copy drifts into clutter | `ux-clarity-review` checks length limits; `design-review` still runs. |
| R3 | Renames break deep links | Redirects for moved settings routes; keep API names. |
| R4 | Uncommitted work on `main` (tracks pages, AI service) overlaps UX-4 and UX-7 | Land or stash it before starting those slices. |
