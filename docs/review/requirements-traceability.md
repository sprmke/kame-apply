# Requirements traceability

**Last updated:** 2026-10-28. Every request in the original brief (message 1) and the follow-up review request (message 2), mapped to where the plan covers it. Status: ✅ covered as asked · 🔁 covered with a deliberate change (reason given) · ⏳ covered in a later release.

## Message 1: original brief

| # | Request (paraphrased) | Where | Status |
| --- | --- | --- | --- |
| 1 | Analyze, critique, and review the user's uploaded resume | PRD F7 · research/05 §3 · Phase 8 | ✅ |
| 2 | Generate or improve the resume from research on in-demand skills | PRD F7 · research/05 §4–5 · Phase 8 | ✅ |
| 3 | AI research of best skills/experience for the target role to raise interview odds | Market insights (real posting data + optional web research) · research/07 · Phases 8–9 | ✅ |
| 4 | Automate filling of job application forms with AI | PRD F8 · research/03 · Phase 13 (extension, R1) · Phase 15 (runner, R2) · Phase 19 (auto-submit) | ✅ ⏳ |
| 5 | Deep research on bypassing bot checks / appearing human to crawl sites | research/02 §5 | 🔁 Declined: evasion breaks ToS, gets user accounts banned, costs money, and breaks weekly. Replaced by compliant layers that reach more jobs, plus a present human for challenges. Same rule as kame-hunt. |
| 6 | Which technologies, MCPs, libraries, scripts are needed for crawling | research/02 §2 · tech-stack §1 · Phase 5 | ✅ |
| 7 | AI crawls the internet and finds the closest-match jobs | PRD F4, F6 · Phases 5–6 | ✅ |
| 8 | Connect/authenticate to LinkedIn, JobStreet, Indeed and other sites to find and apply | Extension in the user's own logged-in browser (Phase 13) · encrypted opt-in ATS sessions in runner (Phase 15) · email alerts (Phase 17) | 🔁 No stored passwords, no logged-in crawling of those platforms; the user's own session + alerts instead. See review/plan-critique §2.1 for LinkedIn specifics. |
| 9 | Quickly copy questions and answer them | Answer Desk · PRD F9 · Phase 12 · extension answer insert (Phase 13) | ✅ |
| 10 | Answers that read human, not AI-generated, to avoid flags | Voice profile + grounded facts + banned phrases (Phase 3, 12) · research/04 §5 | 🔁 We write in the user's real voice from real facts. We don't build AI-detector evasion, and AI-use questions are answered truthfully. |
| 11 | Sites where automation fails even when authenticated → manual help | Extension assist + Answer Desk + "continue in my browser" handoff | ✅ |
| 12 | Wide, fine-grained job settings; support every job on the planet | PRD F3 (20+ dimensions) · ESCO/O*NET taxonomy · Phase 4 · research/02 §4 (honest coverage registry) | ✅ |
| 13 | Best UX: many controls vs text area vs AI-generated prompt | ux-blueprint §4: hybrid (describe → structured chips → live preview → AI suggestions) | ✅ |
| 14 | Folder/module per role (Software Dev, AI Engineer, PM...) with all features per role | **Tracks** · PRD F2 · Phase 4; per-Track resume, criteria, sources, schedule, autonomy, insights, pipeline | ✅ |
| 15 | Pause filling when a "no AI" notice is found; user fills manually; save progress; browser window or terminal input | `ai_restricted` checkpoint · durable DBOS runs · live view (Phase 16) · extension handoff · local runner terminal prompt (Phase 15) | ✅ |
| 16 | Preview AI filling in real time (iframe or better) | Live view via CDP screencast + takeover · research/03 §5 (why iframes can't work) · Phase 16 | ✅ ⏳ |
| 17 | Detect likely scam/phishing jobs, pause, warn, let user decide; don't flag everything | PRD F13 · research/04 · Phase 7 (false-red target < 3%) | ✅ |
| 18 | Schedule crawling frequency; per site/platform or the whole internet; automate applying | PRD F10 · Phase 10 · autonomy levels (`prepare` R1, `assist` R2, `auto-submit` later) | ✅ ⏳ |
| 19 | Dashboard: status, submitted count, flagged items, application previews, to-dos, full management | Command center + tracker · PRD F11 · Phase 11 · ux-blueprint §3.1 | ✅ |
| 20 | Research existing apps; reverse engineer them | research/01 (OSS + commercial + our own kame-hunt) | ✅ |
| 21 | List open roles without automation so the user checks them one by one; help fill one by one | Job research board · PRD F5 · Phase 6 · extension per-job assist | ✅ |
| 22 | Hidden / less-known methods that work | research/02: Common Crawl ATS directory mining, schema.org JobPosting, email-alert ingestion, form-signature caching | ✅ |
| 23 | Reuse best practices, rules, skills, hooks, MCPs from kame projects for Claude Code, Cursor, OpenCode | research/06 · Phase 0 | ✅ |
| 24 | Pick the best tech; prefer Python/.NET/NestJS/Go/Laravel/Rust/Rails; explain | tech-stack §2 (Python chosen, comparison table, runner-ups) | ✅ |
| 25 | Modern tooling like Tailwind; modern full stack | tech-stack §1 (Tailwind v4, Vue 3 + Nuxt 4, Reka UI, TanStack Query/Table for Vue, WXT) | ✅ |
| 26 | Features first, language second; avoid "common" tech unless best | tech-stack §2–3 (DBOS over Redis queues, Typst, CDP relay) | ✅ |
| 27 | Free services first (consider Vercel/Supabase) | tech-stack §5 (+ §5a: why not Vercel/Supabase) | ✅ |
| 28 | Multiple plan docs, ordered, step by step / feature by feature | phases/README + 21 phase files | ✅ |
| 29 | Best agentic coding workflow; scripts, skills, rules; external popular skills | research/06 · Phase 0 | ✅ |
| 30 | Don't build yet | Only docs created | ✅ |
| 31 | Multi-tenancy | architecture §4 · Phase 2 (RLS + app scoping + cross-tenant tests) | ✅ |
| 32 | Best UI/UX, fully responsive | ux-blueprint · every UI phase's exit criteria (375/820/1440 × light/dark) | ✅ |

## Message 2: review and additions

| # | Request | Where | Status |
| --- | --- | --- | --- |
| 33 | Review everything; nothing missed | This document | ✅ |
| 34 | Very detailed plans incl. technology, UX, edge cases | Phase files (tasks per layer, UX, edge cases, testing, exit criteria) · review/plan-critique | ✅ |
| 35 | App must truly help, not be "crappy" | Acceptance scenarios + evals + dogfood gates per phase · PRD §6 metrics · plan-critique §1 | ✅ |
| 36 | MVP = find roles, improve resume, apply, land interviews | PRD §4a | ✅ |
| 37 | Account for recruiters using AI to analyze resumes | research/07 · PRD F18 Recruiter Lens · Phases 6, 8, 9 | ✅ |
| 38 | Tailor resume per job so recruiter AI finds/ranks it | PRD F7 (tailor P0) · research/05 §6 · Phase 9 | ✅ |
| 39 | Research how recruiters find applicants with AI; reverse-engineer criteria | research/07 §1–3 (sourcing, parsing, knockouts, requirement-level AI grading, fraud checks, human skim) | ✅ |
| 40 | Some companies still screen manually | research/07 §2(F) skim view · Lens skim check · DOCX + PDF | ✅ |
| 41 | Optimize for both human and AI | Recruiter Lens (parse + Fit & Gap + knockouts + skim + authenticity) | ✅ |
| 42 | Connect the app to my Claude Code subscription to run agentic actions on all app data/files/configs (message 3) | PRD F21 · research/08 · Phase 12b | 🔁 Your own Claude connects **to** the app (MCP + plugin + agent inbox + your own `claude -p`). The app's server never uses or stores subscription credentials, as Anthropic's terms require. |
| 43 | Frontend must not be React; pick Vue, Angular, or a better fit (message 4) | tech-stack §1, §2a (Vue 3 + Nuxt 4 chosen; Angular runner-up) · Phases 0, 1, 2, 13 updated | ✅ |
| 44 | Brand-new design system and UI/UX, not like other Kame apps (message 4) | design/design-system.md ("Field Notes") · ux-blueprint rewritten · Phase 2 design tasks · research/06 (rewrite, don't port, UI tooling) | ✅ |
