# Research 01: Landscape of existing products and open-source projects

**Researched:** 2026-10-28. Star counts and claims come from READMEs and aggregators and were not independently verified.

Goal: don't rebuild what exists. Borrow proven designs and avoid known failure modes.

## 1. Our own prior art (highest value: proven by us, same rules)

### `../kame-hunt` (Bun + TS, personal CLI, built 2026-10-23)

Already works end to end for one user. Kame Apply is effectively **kame-hunt turned into a multi-tenant web product**. Port these ideas (rewrite in Python per [`tech-stack.md`](../tech-stack.md)):

| kame-hunt piece | What it does | Kame Apply destination |
| --- | --- | --- |
| `src/sources/ats.ts`, `boards.ts` | Greenhouse/Lever/Ashby/Workable + Himalayas/RemoteOK/Remotive/HN/Arbeitnow fetchers, normalized `Job[]` | Phase 5 source adapters |
| `src/sources/linkedin-jobstreet.ts` | Logged-out public search reads | Phase 5 "personal-mode" adapters (off by default, see research/02) |
| `src/filter.ts` + `ai-score.ts` | Cheap rule filter before AI; AI only on eligible/unclear | Phase 6 ranking funnel |
| `config/companies.yaml` + `companies:check` | ATS slug directory with validation | Phase 5 company directory (grown automatically) |
| `profile/master-profile.yaml` + `answers.yaml` | Single source of truth, answer bank | Phase 3 Career Profile |
| `src/resume/` (schema + Playwright PDF render) | Structured resume to PDF | Phase 8 (moved to Typst/RenderCV) |
| `src/apply/extract.ts`, `mapper.ts`, `fill.ts` | Form field extraction, LLM mapping to profile, fill | Phase 13 runner core |
| `src/apply/human.ts` | "Your turn" overlay with Continue/Skip/I submitted + notification | Phase 13 checkpoints (moved into the app + live view) |
| `src/apply/sites.ts` + `site_caps` | Per-site daily caps | Phase 10/15 caps |
| `docs/06-safety-and-scam-detection.md` + `/vet` | Red/yellow/green checklist, data-sharing stages | Phase 7 scam engine rules |
| `CLAUDE.md` non-negotiable rules 1–7 | Never fabricate, human clicks submit, no CAPTCHA bypass, truthful AI answers, stop on sensitive data, untrusted content | `prd.md` principles P1–P6 |

### `../kame-desk` (FastAPI + TanStack Start, production-grade)

Kame-desk is the **backend and process** template (Kame Apply's frontend is Vue/Nuxt with its own design system, so kame-desk's React UI isn't reused): FastAPI owns business logic, the frontend owns UI only, SQLAlchemy 2 async + Alembic, pgvector, tenant scoping (`clinic-scoping` skill), RBAC + append-only audit log, PydanticAI with draft-then-confirm, SSE streaming, WebSockets, Orval-generated TS client, and the full Claude/Cursor/OpenCode tooling. See [`06-agentic-workflow.md`](./06-agentic-workflow.md) for the port list.

### `../kame-pick`

Candidate analysis/scoring rubric from the **recruiter** side (`.cursor/skills/analyze-job-candidates/scoring-rubric.md`). Useful as a source for how screeners score resumes. Reuse it as an input to the Phase 8 critique rubric.

### `../kame-homes`, `../kame-lends`, `../kame-finance`

Multi-tenancy patterns (`multi-tenancy` skill), the Gmail listener (`gmail-listener` skill, useful for Phase 16), design system and anti-slop tooling (`impeccable`, `DESIGN.md`, `PRODUCT.md`), workflow scratchpads, docs-first discipline.

## 2. Open-source projects (2026)

| Project | License | What it is | Borrow | Avoid |
| --- | --- | --- | --- | --- |
| **AI Job Search** (MadsLorentzen/ai-job-search) | MIT | Claude Code workflow: `/scrape /rank /apply /interview /outcome /gmail-sync`; portal skills as CLIs; drafter → fresh-context reviewer → revise pipeline; LaTeX CV with visual page check | **Drafter/reviewer loop** for tailoring; **`posting_guard`** (strip hidden text, flag injection-shaped lines in postings); robots.txt check before retries; "keyword gaps shown as gaps, not inserted"; Gmail sync proposes status changes, writes only on approval; Language Gate | Claude-Code-as-runtime (not a web product) |
| **ApplyPilot** (Pickle-Pixel → ibarrajo fork, ApplyPilot-Plus) | **AGPL-3.0** | Python 7-stage pipeline: discover → enrich → score → tailor → cover letter → auto-apply → track; JobSpy + 48 Workday portals + 30 career sites; Claude Code + Playwright MCP as apply agent; 5 parallel Chrome workers; Gmail tracking | Stage pipeline shape; **Workday portal list idea**; locked `resume_facts`; LLM fallback chain on rate limits; HITL pause in the same Chrome session; CDP status badge | **Don't copy code** (AGPL would force our whole service open). Don't copy its CapSolver CAPTCHA solving, `--no-hitl` overnight mode, or "1,000 jobs in 2 days" volume approach. |
| **AIHawk / Jobs_Applier_AI_Agent** (feder-cr) | AGPL | The 2024 viral LinkedIn Easy Apply bot, later reduced to resume/cover-letter generation | Its history is the lesson: LinkedIn-account automation got users restricted and the project retreated from it | Logged-in LinkedIn automation |
| **JobSpy** (python-jobspy) | MIT | Scrapes LinkedIn/Indeed/Glassdoor/ZipRecruiter/Google (forks add Bayt, Naukri) | Normalized job schema ideas; optional personal-mode adapter | Maintainers warn the boards block aggressively; ~1000 results cap; ToS risk at multi-tenant scale |
| **Job Copilot** (pouladzade/job-copilot) | open source | Browser extension: autofill + resume alignment, BYO AI key, local data, never auto-submits; Chrome/Firefox/Safari | **Closest to our extension design.** Read its field-detection heuristics before building Phase 12 | |
| **BeamApply** | open source | Deterministic Firefox autofill from a profile (Greenhouse) | Deterministic-first filling, LLM only for the unknowns | |
| **Autofill-Jobs** (andrewmillercode) | open source | Chrome extension for Greenhouse/Lever/Dover/Workday (unmaintained) | Workday selectors as a reference | |
| **browser-use** | MIT | Python LLM browser agent | Fallback agent for unknown forms (Phase 13) | Using it for every step (slow, expensive); it's a fallback |
| **Skyvern** | AGPL (core) | Vision + LLM form-filling agent, strong on forms | Ideas only (license) | Code reuse |
| **Stagehand** | MIT | TS AI layer over Playwright with action caching | Idea: **cache resolved actions per ATS form** so repeat forms cost no LLM calls | |
| **Reactive Resume** v5 | MIT | Open-source resume builder with its own JSON schema | Template/editor UX reference | |
| **RenderCV** | MIT | YAML → Typst → ATS-friendly PDF (Python) | **Use it** for rendering (Phase 8) | |
| **OpenResume** | AGPL | In-browser resume parser + builder | Its parser heuristics as test ideas | Code reuse |
| **ESCO / O*NET** | open data | Global occupation + skills taxonomies (ESCO: ~3k occupations, ~13k skills, 28 languages; O*NET: US SOC) | **Use both** as the backbone for "every job on the planet" (Phase 4) | |

## 3. Commercial products (reverse-engineered from public behavior)

| Product | Model | Lesson |
| --- | --- | --- |
| **Simplify Copilot** | Free extension autofill + job tracker; jobs list | Users love **one-click autofill in their own browser** + automatic tracking of what they applied to. Our Phase 12 extension is this, plus Tracks and safety. |
| **Jobright.ai** | AI job matching feed + "why you match" + insider connections | Ranked feed with **explainable match reasons** and skill-gap chips drives engagement → Phase 6 UI. |
| **Teal / Huntr** | Tracker + job clipper extension + resume builder with keyword match | **Clipper extension** that saves any job page (incl. LinkedIn) the user is viewing is the accepted way to cover gated boards → Phase 12. |
| **LazyApply / Sonara (shut down) / JobCopilot / Massive** | Mass auto-apply | Generic applications get ~2–3% response; account bans; poor reviews. Volume isn't the moat; relevance + quality is. |
| **Careerflow / Kickresume / Rezi** | AI resume review + ATS score | ATS score is a marketing number. We show concrete line-level fixes and evidence from real postings instead of a magic score. |
| **LinkedIn / Indeed own AI features** | Built-in "apply with AI" assistants | Platforms automate on their own terms; third-party bots get banned. We stay outside their walls. |

## 4. What makes Kame Apply different

1. **Market-evidence resume advice**: skill demand computed from the actual postings in each Track, not generic tips.
2. **Tracks**: several job searches in parallel, each with its own resume, criteria, schedule, and autonomy.
3. **Safety-first automation**: scam scoring + PII guard + checkpoints, with live view and takeover.
4. **Coverage without bans**: ATS directory + public APIs + email-alert ingestion + user-driven clipping.
5. **Truthful in the user's voice**: no fabricated facts, answers grounded in profile + style.
6. **Free to run**, BYO AI key or local model.
