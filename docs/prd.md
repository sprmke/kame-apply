# Kame Apply: Product Requirements (PRD)

**Version:** 0.1 (planning) · **Last updated:** 2026-10-28 · **Owner:** Michael Manlulu

This is the authoritative scope document. Stack lives in [`tech-stack.md`](./tech-stack.md); build order lives in [`phases/README.md`](./phases/README.md).

---

## 1. Vision

Help a job seeker land more interviews by doing the boring 80% of a job search automatically and doing the important 20% better:

1. **Find** every relevant open role (any role, any country) on a schedule, without the user babysitting job boards.
2. **Filter** out scams, ineligible roles, and poor fits before the user sees them.
3. **Strengthen** the resume with evidence from real, current job postings, never with invented experience.
4. **Apply** faster: prefilled forms, tailored resumes, answers in the user's own voice, live preview of what the AI is doing, and a clean handoff whenever a human must act.
5. **Track** every application, flag, and pending action in one place.

### Product principles (non-negotiable)

| # | Principle | What it means in practice |
| --- | --- | --- |
| P1 | **Truthful by construction** | Resumes, cover letters, and answers only use facts in the user's Career Profile. AI may rephrase, reorder, and emphasize. It never invents employers, titles, dates, metrics, degrees, or skills. Skill gaps are shown as gaps, not inserted. |
| P2 | **The human is the human** | We never fake being human. No CAPTCHA solving, no fingerprint spoofing, no proxy rotation, no "humanized" mouse movement to fool bot detection. When a site asks for a human, the app pauses and hands control to the user. See [`research/02`](./research/02-job-discovery-and-site-access.md#5-the-bypass-question). |
| P3 | **User owns every irreversible step** | Default: AI fills everything, the user clicks Submit. Auto-submit is an explicit opt-in per Track, only on allowlisted company ATS forms, only for jobs that pass safety checks. Never on LinkedIn, Indeed, JobStreet, or other platforms whose terms forbid it. |
| P4 | **Warn, don't block** | Scam detection gives a clear risk level with reasons and lets the user decide. Only sensitive-data fields (government ID, bank, card, full DOB) hard-stop automation. |
| P5 | **Respect the source** | Prefer official/public APIs and feeds. Fetch politely, cache, link back to the original posting, never republish listings outside the user's workspace. |
| P6 | **Untrusted input stays data** | Job descriptions, recruiter emails, and web pages are data, never instructions to the AI. |
| P7 | **Free to run** | Every core feature works on free tiers or self-hosted software. Paid services are optional add-ons. |

## 2. Users and tenancy

| Persona | Need |
| --- | --- |
| **Solo job seeker** (primary; Michael is user zero) | Find remote/local roles across several role types at once, apply faster, avoid scams. |
| **Career switcher** | Understand which skills a target role demands and what's missing. |
| **Career coach / recruiter agency / bootcamp** (later) | Manage several candidates in one workspace, each with their own profile, tracks, and pipeline. |

**Multi-tenancy model:** `Workspace` is the tenant. A workspace has members (roles: `owner`, `admin`, `member`, `viewer`) and one or more **Candidate Profiles** (one for a solo user, many for a coach). Every candidate-owned record is scoped to the workspace and isolated by Postgres Row-Level Security. Public job data (postings, companies) is stored once globally and overlaid with private per-workspace state (scores, status, notes). See [`architecture/overview.md`](./architecture/overview.md#4-multi-tenancy).

## 3. Core concepts (glossary)

| Term | Meaning |
| --- | --- |
| **Career Profile** | The single source of truth for a candidate: experience, education, projects, skills, certifications, links, work authorization, location, salary expectations, writing voice, answer bank. Built from uploaded resumes + interview-style Q&A. |
| **Track** | The "folder/module per role" the user asked for, e.g. *Software Developer*, *AI Engineer*, *Product Manager*. Each Track has its own search criteria, sources, schedule, autonomy level, resume variant, answer overrides, and pipeline. All features work per Track. |
| **Criteria** | The structured definition of what a Track looks for (titles, occupations, skills, seniority, location/remote, countries, eligibility, salary, company filters, exclusions...). Edited through natural language or structured controls. |
| **Source** | Where jobs come from (ATS API, job board API, RSS, email alerts, browser-extension clips, company career pages). |
| **Job** | A normalized, deduplicated posting (global). A **Track Job** is that job seen through one Track (match score, risk, status). |
| **Application** | The user's application to a Track Job, with its resume version, cover letter, answers, run history, and status timeline. |
| **Run** | One automated attempt to fill an application form. Durable: can pause for a human and resume later from saved progress. |
| **Checkpoint** | A pause where the human must act: login, CAPTCHA, "answer without AI" field, sensitive field, risky job, final Submit. |
| **Autonomy level** | Per Track: `discover` → `prepare` → `assist` → `auto-submit` (see F8). |

## 4. Features

Feature IDs are referenced by phase files. Priority: **P0** = MVP, **P1** = v1, **P2** = later.

### F1. Career Profile and resume intake (P0)

- Upload existing resume(s) (PDF, DOCX, TXT, LinkedIn PDF export) and portfolio. Parse into structured facts with per-field confidence. The user confirms or corrects every field.
- Guided "profile interview" (chat) to fill gaps: metrics behind bullets, tools used, team size, scope, outcomes.
- **Answer bank:** reusable facts for forms (work authorization, notice period, salary expectations, relocation, pronouns optional, EEO answers optional and default "prefer not to say", how-did-you-hear defaults, links).
- **Writing voice:** user pastes 2–5 samples of their own writing (emails, Slack messages, cover letters). The system extracts a style profile (sentence length, formality, vocabulary, banned phrases) used for all free-text answers.
- Sensitive data (government IDs, bank) is **never** stored in the profile.

### F2. Tracks: role folders (P0)

- Create, duplicate, archive, and reorder Tracks. Templates for common roles; any role in the world can be created (backed by the ESCO + O*NET occupation taxonomy plus free text).
- Each Track has: criteria, sources, schedule, autonomy level, linked resume variant, cover-letter style, answer overrides, notification rules, and its own pipeline and stats.
- A Track dashboard shows: new matches, ready to apply, in progress, needs you, applied, responses, interviews, flagged.

### F3. Criteria builder: fine-grained job settings (P0)

The UX decision (detailed in [`design/ux-blueprint.md`](./design/ux-blueprint.md#4-criteria-builder-decision)): **a hybrid, not one or the other.**

1. **Describe it**: a text box ("Senior React or full-stack roles, remote from the Philippines or APAC timezone, ≥ $4k/month, no crypto, no agencies"). AI compiles it into structured criteria.
2. **Structured controls**: the compiled criteria appear as editable chips and sections. Every control is also directly editable, and edits update the description summary.
3. **Live preview**: an estimated match count and sample matches update as criteria change, so the user sees the effect of each filter.
4. **"Improve my criteria"**: AI suggests synonyms/adjacent titles ("Frontend Engineer", "UI Engineer"), skill expansions, and filters that remove noise, based on the jobs already seen.

Criteria dimensions (all optional): job titles + synonyms; occupation codes (ESCO/O*NET/ISCO); must-have / nice-to-have / excluded skills; seniority; employment type (full-time, part-time, contract, freelance, internship, temporary); work mode (remote, hybrid, on-site); remote eligibility (worldwide, region, country list, timezone overlap window); locations with radius; visa sponsorship / relocation; salary min/max, currency, period, "hide if unspecified"; company include/exclude lists, size, industry, funding stage, public/private; recruiters/agencies allowed or not; posting age; language requirements; education requirements; security clearance; keywords include/exclude (boolean expressions); minimum match score; maximum applications per day.

### F4. Job discovery engine (P0)

- Pulls from many sources per Track on a schedule (F10): company ATS APIs (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Personio, Workday public job endpoints, and others), job-board APIs (Adzuna, Jooble, Careerjet, USAJobs, Remotive, Remote OK, Himalayas, Arbeitnow, HN "Who is hiring", etc.), RSS feeds, schema.org `JobPosting` data on company career pages, email job alerts the user forwards, and jobs clipped with the browser extension.
- **Company directory**: continuously grows a list of companies and their ATS boards (discovered from Common Crawl, posting links, and user clips), so coverage grows without scraping gated sites.
- Normalizes, deduplicates across sources (same job on 5 boards becomes 1 job with 5 links), detects reposts, and expires closed jobs.
- Full source catalog and per-country coverage: [`research/02`](./research/02-job-discovery-and-site-access.md).

### F5. Job research board: browse without automation (P0)

The "just find me the jobs so I can check them one by one" feature.

- A fast, filterable, sortable job list per Track and across Tracks: match score, why it matched, missing skills, salary, location/eligibility, source, posted date, risk badge.
- Job detail drawer: full description (sanitized), highlights, red/yellow flags, company info, similar jobs, "open original" link.
- Actions: shortlist, skip (with reason, which trains the ranking), hide company, mark applied manually, **prepare application** (F7/F11), **open with assist** (extension or runner), export CSV.
- Saved views and keyboard-driven triage (j/k, s shortlist, x skip, o open).

### F6. Matching and ranking (P0)

- Hard filters from criteria (eligibility, location, exclusions) → cheap rule score → semantic similarity (embeddings of profile vs job) → LLM fit assessment only for the top candidates (cost control).
- Output per Track Job: score 0–100, reasons, matched skills, missing must-haves, eligibility verdict (`eligible` / `unclear` / `not eligible` with quote from the posting), seniority fit, salary fit.
- Learns from user feedback (shortlist/skip reasons) per Track.

### F7. Resume intelligence (P0 → P1)

- **Critique & review** (P0): ATS parseability, structure, impact/quantification per bullet, keyword coverage vs the Track's market data, length, tense, clichés, formatting. Scored rubric with concrete, line-level suggestions.
- **Market research** (P0): for each Track, aggregate the skills, tools, certifications, and experience patterns across all matched postings (real data, refreshed continuously), plus optional AI web research. Shows: top demanded skills with frequency and trend, which ones the user has (and whether the resume shows them), which are gaps, which are "you have it but didn't list it."
- **Generate or improve** (P0): produce an improved base resume per Track from the Career Profile + market data. Every change is shown as a diff with the reason; the user accepts or rejects each.
- **Tailor per job** (**P0, MVP**): for a job the user really wants, one click produces the best truthful resume for *that* posting. It extracts every qualification from the posting, maps each to evidence in the Career Profile, rewrites the summary and bullets so each must-have is evidenced in the posting's own terminology, reorders by relevance and recency, and runs the **Recruiter Lens** (F18) before and after so the user sees the predicted improvement. Every change is shown as a diff with a reason; unsupported requirements are listed as gaps, never inserted. Optional cover letter in the user's voice. Versions are saved per application, so the exact file sent is always known.
- **Render** (P0): ATS-safe PDF and DOCX from structured data (single column, real text layer, standard headings). A few clean templates.
- **Gap plan** (P2): learning suggestions for real gaps (course, project idea), never resume padding.

### F8. Assisted and automated applying (P1)

Per-Track **autonomy level**:

| Level | Behavior |
| --- | --- |
| `discover` | Find, rank, and flag jobs only. |
| `prepare` | Also produce tailored resume, cover letter, and draft answers for shortlisted jobs; user applies themselves. |
| `assist` (default for applying) | The app fills the whole form (via extension or cloud runner), pauses at checkpoints, and **the user clicks Submit**. |
| `auto-submit` | Opt-in. Submits without the final click **only if**: the form is on an allowlisted company ATS (not LinkedIn/Indeed/JobStreet/other ToS-restricted platforms), the job's risk level is green, the match score is above the Track threshold, every free-text answer is from approved answers or was approved in a batch review, no checkpoint fired, and the daily cap isn't reached. Anything else falls back to `assist`. |

Two execution paths (details in [`research/03`](./research/03-apply-engine-and-live-view.md)):

- **Browser extension (primary for logged-in sites):** runs in the user's own browser where they are already logged in. Fills fields on the current page from the profile, tailored resume, and drafted answers. Works on company ATS forms, Workday, and generic forms by default. LinkedIn Easy Apply, Indeed, and JobStreet autofill is off by default and opt-in with a terms acknowledgment, because those platforms' terms restrict browser add-ons (see `review/plan-critique-and-risks.md` §2.1).
- **Cloud runner:** a headless browser on our worker fills company-ATS forms end to end, streams a live view to the app, and pauses for checkpoints.

Checkpoints that always pause (both paths): login or account creation, CAPTCHA or "verify you are human", any field or page that says not to use AI, any sensitive field (government ID, bank, card, full DOB, full street address before an offer), free-text questions without an approved answer (in `assist`), red/yellow risk jobs, unknown required fields, and final Submit (unless `auto-submit`). Progress is saved at every step; a paused run can be resumed hours later from the app, the extension, or the live view.

### F9. Answer Desk: quick copy-paste answers (P1)

For sites where nothing can be automated:

- Paste one or many questions (or capture them from the page with the extension). AI drafts answers in the user's voice using only Profile facts; each has a one-click copy, character counter, and "shorter / more specific / more casual" controls.
- Answers can be saved back to the answer bank so the next form reuses them.
- Answers are written in the user's voice: plain, specific, no stock AI phrases (banned-phrase list + style profile). The goal is that answers sound like the user because they are grounded in the user's real facts and real writing. We do **not** try to defeat AI detectors, and questions about AI use are answered truthfully.
- If a question says "do not use AI", the Answer Desk does not draft it. It shows the question with relevant profile facts as notes so the user can write it themselves.

### F10. Scheduling and automation (P0 → P1)

- Per Track and per source: run frequency (every hour, every N hours, daily at a time, weekdays only, custom cron), quiet hours, time zone.
- Scope per schedule: all enabled sources, a specific source/site, or "the whole internet" (all sources the Track has enabled).
- Automation chain per schedule: discover → score → safety check → (prepare) → (queue for assist / auto-submit) → notify.
- Rate limits and caps: per source politeness limits, per Track daily application cap, per site daily cap.
- Run history with counts, errors, and duration.

### F11. Application tracker and command center (P0)

- **Command center (home):** status at a glance: jobs found today/week, matched, applications submitted (today/week/total), response rate, interviews, active runs, **Needs you** inbox (checkpoints, approvals, scam warnings, failed runs), flagged jobs, upcoming scheduled runs, per-Track summary cards.
- **Pipeline per Track:** kanban + table: `new → shortlisted → preparing → ready → in progress → needs you → submitted → responded → interview → offer → rejected / withdrawn / ghosted`.
- **Application detail:** job snapshot (frozen copy of the posting at apply time), resume version used, cover letter, every answer submitted, run timeline with screenshots, checkpoint history, emails received, notes, follow-up reminders.
- Manual applications can be logged too (one click from job detail or the extension).

### F12. Live preview and takeover (P1)

- Watch the cloud runner fill a form in real time inside the app (streamed browser view; an iframe can't work because sites block framing).
- Step list beside the view: what was filled, with which value and source fact.
- **Take over**: click into the live view to type or click yourself (login, CAPTCHA, a tricky field), then **Hand back** to resume automation.
- After a run: a replay (screenshots per step) is kept with the application.

### F13. Scam, phishing, and safety guard (P0)

- Every job gets a risk level `green / yellow / red` with human-readable reasons, from layered signals: content rules, domain and email intelligence, link reputation, cross-checks against the company's own careers site, an ML classifier, and an LLM judgment.
- Red or yellow pauses automation for that job and shows a warning with **Continue anyway** / **Skip** / **Report**. Nothing is silently blocked.
- PII guard: field-level sensitivity classification on every form; sensitive fields always stop for the human.
- Recruiter-message and take-home vetting: paste a message, link, or repo URL to check for known scam patterns (fake coding tests that install malware, payment requests, chat-only interviews).
- Details: [`research/04`](./research/04-trust-safety-and-scam-detection.md).

### F14. Email integration (P1)

- **Inbound alerts:** each workspace gets a private forwarding address. The user forwards (or auto-forwards) job-alert emails from LinkedIn, JobStreet, Indeed, Glassdoor, and others. The system parses them into jobs. This is how gated platforms get covered without scraping them.
- **Response tracking (P2):** optional Gmail/Outlook connection, or forwarding of recruiter replies, to auto-move applications to `responded / interview / rejected` (proposed, user confirms).

### F15. Notifications (P1)

In-app notification center, email digest, web push (PWA), and optional Telegram bot. Per-event preferences: new strong matches, needs-you checkpoints, scam flags, run failures, daily/weekly digest.

### F16. AI provider and cost controls (P0)

Bring-your-own key per workspace (Gemini, OpenAI, Anthropic, Groq, OpenRouter) or a local model via Ollama. Per-workspace monthly AI budget, usage meter, and model routing (cheap model for bulk scoring, strong model only for tailoring and on explicit user action). Provider data-use notes are shown, and users can keep personal data (profile, tailoring, answers) off free tiers that may train on inputs (see `tech-stack.md` §5b).

### F17. Interview prep (P2)

Per application: company brief, likely questions from the posting, STAR stories from the profile.

### F18. Recruiter Lens: see the application the way the employer's AI and humans will (P0)

Grounded in [`research/07`](./research/07-how-recruiters-find-and-screen.md). For any resume + job pair:

1. **Parse check:** our generated PDF/DOCX is re-parsed by two independent parsers; contact, titles, companies, dates, and sections must survive in order. Failures block export with a fix.
2. **Qualification Fit & Gap:** every qualification extracted from the posting (must-have / preferred) gets a verdict *met / partially met / not evidenced / not met* with the quoted resume evidence, plus an overall A–D grade modeled on how modern ATS AI grades (requirement-by-requirement, not keyword counting).
3. **Knockout prediction:** work authorization, location/timezone, years, degree/license, salary, language, from posting vs answer bank.
4. **7-second skim view:** what a human sees in the top third of page one, with a checklist.
5. **Authenticity check:** consistency with the Career Profile and LinkedIn text, generic-phrase detection, unverifiable claims.

The Lens is a simulation with stated limits. It never promises "ATS score 98%".

### F19. Be Found: inbound visibility (P1)

Recruiters source candidates in LinkedIn Recruiter and in their ATS databases. Per Track: suggested LinkedIn headline, About, top skills order, and experience-title wording (truthful, copy-paste, no LinkedIn automation); "Open to work (recruiters only)" setup checklist; resume ↔ LinkedIn consistency report; GitHub/portfolio checklist where relevant.

### F20. Smart application strategy (P1)

Freshness boost (apply within 24–72 h of posting), canonical company-ATS apply links over aggregator apply, per-company application cap (avoid looking like a spammer to one employer's ATS), follow-up reminders with drafted messages the user sends, salary-range suggestions from posting + market data.

### F21. Bring your own Claude: Claude Agent Bridge (P0)

Connect the user's own Claude (Claude Code, Claude Desktop, claude.ai) to their Kame Apply workspace so it can do the agentic work on their subscription with full access to their data: profile, resumes and files, Tracks and criteria, jobs, answers, applications. Delivered as a remote **MCP server** (OAuth, scoped per workspace), a **Claude Code plugin** (commands, skills, reviewer agent, guard hooks), an **agent inbox** (route any heavy AI feature to "my Claude"; processed interactively with `/kame:work`, headless by the user's own `claude -p` on their own machine, or by a routine the user creates), and optional guided applying with Claude in Chrome. Per Anthropic's terms, Kame Apply never collects, stores, or relays Claude credentials, and never runs server-side work on a user's subscription. Every write is a draft behind the same truthfulness, safety, and parse checks. Details: [`research/08`](./research/08-bring-your-own-claude.md).

## 4a. MVP definition (Release 1)

**MVP goal:** a user finds real matching jobs, improves their resume with market evidence, tailors a resume per job that passes both AI screeners and a human skim, applies faster with help, and lands more interviews.

| In MVP (Release 1) | Release 2 | Later |
| --- | --- | --- |
| F1 Profile & intake · F2 Tracks · F3 Criteria builder · F4 Discovery (Layers 1–3 + clips) · F5 Research board · F6 Matching · F7 Critique, market research, improve, **per-job tailoring**, render · F18 Recruiter Lens · F13 Scam & safety · F10 Scheduled discovery · F11 Tracker & command center · F9 Answer Desk · F12-lite extension (clip + autofill + log applied) · F16 AI keys & budget · F21 Claude Agent Bridge | F8 Cloud runner `assist` + F12 live view/takeover · F14 email alert ingestion · F15 push/Telegram · F19 Be Found · F20 strategy | F8 `auto-submit` · response tracking · F17 interview prep · referrals · coach/agency workspaces UI |

Why this order: the evidence in [`research/07`](./research/07-how-recruiters-find-and-screen.md) says relevance and resume quality drive interviews, while volume automation drives spam and bans. Release 1 delivers most of the interview-rate gain. The extension gives most of the time saving on any site with no bot risk. The cloud runner is the most complex and riskiest piece and ships second.

## 5. Out of scope / explicit non-goals

- Evading bot detection in any form: CAPTCHA solvers, stealth/fingerprint plugins, residential proxy rotation, faked human input patterns, scraping while logged in to platforms whose terms forbid it.
- Mass "spray and pray" applying. Caps and quality gates are product features, not limitations.
- Fabricating or embellishing experience, generating fake references, or answering eligibility/authorization questions untruthfully.
- Storing passwords for third-party job sites. Logins happen in the user's browser or during live takeover; only session state is kept, encrypted, and the user can revoke it.
- Sending messages to recruiters on the user's behalf without explicit per-message approval.

## 6. Success metrics

| Metric | Target (first 3 months of personal use) |
| --- | --- |
| Interview rate per submitted application | ≥ 2× the user's pre-Kame baseline |
| Median time from "job found" to "submitted" (assist mode) | < 4 minutes of human time |
| Scam/phishing jobs reaching "submitted" | 0 |
| False red flags on legitimate company-ATS jobs | < 3% |
| Fabricated facts in generated documents (sampled audit) | 0 |
| Monthly running cost | $0 infra; AI within the user's free-tier/BYO budget |

## 7. Open questions (decide during the listed phase)

| Question | Decide in |
| --- | --- |
| Public sign-up at launch, or invite-only personal/beta? (Affects Gmail OAuth verification and abuse controls.) | Phase 2 |
| Which countries' job boards to prioritize after global ATS coverage (PH, SG, AU, US, EU)? | Phase 5 |
| Should auto-submit exist in v1 at all, or ship `assist` only and add it after real usage data? | Phase 15 |
| Monetization (if ever): keep free + BYO key, or paid hosted AI? | After Phase 17 |
