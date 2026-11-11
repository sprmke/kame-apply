# Tech stack

**Authoritative** technology choices for Kame Apply. Update this file when the stack changes. Scope lives in [`prd.md`](./prd.md).

**Last updated:** 2026-11-02 · **Status:** Phase 1 spikes decided (Oracle Keep + Hetzner fallback; live A1 = operator).

## 1. Decision summary

| Layer | Choice | Why (one line) |
| --- | --- | --- |
| Core language (backend, workers, crawler, apply runner) | **Python 3.13** | Best ecosystem for every hard feature: browser automation, AI agents, scraping/parsing, ML scam detection, resume rendering. |
| API framework | **FastAPI** + Pydantic v2 | Async, typed, OpenAPI out of the box; proven in kame-desk (reuse its skills/rules). |
| Durable workflows, scheduling, queues | **DBOS Transact (Python)** 🔬 | Postgres-backed durable workflows: pause for a human for hours, resume from the last completed step, cron schedules, rate-limited queues. **No Redis, no extra server.** |
| ORM / migrations | SQLAlchemy 2 (async) + Alembic | Kame-desk pattern. |
| Database | **PostgreSQL 17** + pgvector + pg_trgm + RLS | One store for app data, vectors, full-text, workflow state, multi-tenant isolation. |
| AI orchestration | **PydanticAI** | Typed structured outputs, provider-agnostic (Gemini/OpenAI/Anthropic/Groq/OpenRouter/Ollama), kame-desk pattern. |
| Embeddings | **fastembed** (ONNX, CPU, local) | Free; `bge-small-en-v1.5` + `multilingual-e5-small` for non-English. |
| Browser automation | **Playwright (Python)** + **browser-use** as fallback agent | Deterministic adapters first, LLM agent only for unknown forms. |
| Live view | CDP `Page.startScreencast` → FastAPI WebSocket → `<canvas>` | Works where iframes can't; supports takeover via `Input.dispatch*`. |
| Crawling / parsing | httpx, selectolax, extruct (JSON-LD), feedparser; Crawl4AI optional | Fast, polite, no headless browser unless needed. |
| Resume parsing | markitdown + pdfplumber + python-docx (+ docling optional 🔬) → LLM structuring | MIT/BSD licenses (avoid AGPL PyMuPDF). |
| Resume rendering | **RenderCV (Typst)** for PDF, python-docx for DOCX | ATS-safe, real text layer, fast, Python-native. |
| Scam ML | scikit-learn (TF-IDF + logistic regression / gradient boosting on EMSCAD) | Tiny, explainable, runs on CPU. |
| Frontend | **Vue 3.5 + Nuxt 4 + TypeScript** (app routes as SPA `ssr: false`; marketing/legal pages prerendered) | New for the Kame portfolio (others are React or Svelte); first-class in WXT so web and extension share one component library; strong fit for form- and data-heavy UI. UI only, no business logic. See §2a. |
| UI | **Tailwind CSS v4** + **Reka UI** headless primitives + `tailwind-variants`, custom components in `packages/ui`; **Phosphor** icons via `@nuxt/icon`; **Motion for Vue** (`motion-v`) scoped | New "Signal" design system ([`design/design-system.md`](./design/design-system.md)), deliberately unlike the other Kame apps (no shadcn look, no Lucide, no teal). |
| Server state / client state | **TanStack Query for Vue** (`@tanstack/vue-query`), **Pinia** (UI state only), **VueUse** | Same caching model as before, idiomatic Vue. |
| Forms / validation | **VeeValidate + Zod** (schemas generated from OpenAPI) | Typed forms; same Zod schemas in the extension. |
| Tables / lists / charts | TanStack Table (Vue) + TanStack Virtual; **ECharts** via `vue-echarts` | Large virtualized job lists; themed charts. |
| API client | **Hey API `openapi-ts`** with the `@tanstack/vue-query` plugin 🔬 (fallback: Orval `vue-query` client) | Typed end to end Python ↔ TS; the plugin was labeled beta in some docs, so it's checked in the Phase 1 spike. |
| i18n / PWA | `@nuxtjs/i18n`, `@vite-pwa/nuxt` | Locale-aware from day one; installable PWA for push and offline read. |
| Browser extension | **WXT** (MV3, Vite) + **Vue** + shared `packages/ui` | Chrome/Edge/Firefox from one codebase; side panel UI with the same components as the web app. |
| Realtime | WebSockets (live view, run events), SSE (AI streaming) | |
| Agent integration | **Official MCP Python SDK** (Streamable HTTP mounted in FastAPI) + Authlib OAuth AS; Claude Code plugin (marketplace repo); `kame-agent` CLI (uv tool) wrapping the user's own `claude -p` | Bring-your-own-Claude within Anthropic's terms ([`research/08`](./research/08-bring-your-own-claude.md)). |
| Auth | FastAPI JWT access + refresh (kame-desk `fastapi-jwt-auth`), Google OAuth via Authlib, argon2 passwords | Free, no vendor lock. |
| Files | Cloudflare R2 (S3 API); MinIO locally | 10 GB free, no egress fees. |
| Email out / in | Resend (out, free tier) · Cloudflare Email Routing + Email Worker (in, free) | Inbound alerts without restricted Gmail scopes. |
| Notifications | In-app + Web Push (PWA) + Telegram Bot API (optional) | All free. |
| Observability | Sentry (free) + structured JSON logs; Pydantic Logfire free tier optional | |
| Monorepo | pnpm workspaces + Turborepo (TS) · **uv** workspace (Python) | Kame-desk pattern. |
| Quality | ruff (lint+format), basedpyright, pytest; ESLint + Prettier, Vitest, Playwright E2E | |

## 1a. Phase 1 spike outcomes

Notes in [`architecture/spikes/`](./architecture/spikes/README.md). All 🔬 items kept; none dropped.

| 🔬 item | Outcome |
| --- | --- |
| DBOS | **Keep.** Survived `SIGKILL` mid-`recv` with step 1 run once; queues with partition concurrency + rate limits and DB-backed cron schedules work. API differs from older docs (no `@DBOS.scheduled`, `DBOS.register_queue` after launch). |
| Hey API + Vue Query | **Keep.** Strict TS clean, discriminated unions narrow, reactive `computed` params refetch. Do not depend on the deprecated `@hey-api/client-fetch` package. |
| RenderCV/Typst | **Keep.** 0.6 s render, real text layer, correct reading order. |
| WXT + shared UI | **Keep.** Same `@kame/ui` component and tokens in Nuxt and the side panel; 39.6 kB gzipped. |
| CDP screencast | **Keep** locally (28 fps, 5 KB frames, input dispatch works); internet leg pending a host. |
| fastembed | **Keep.** ~51 texts/s and ~800 MB RSS on a laptop; plan 3-5x slower on the VM. |
| Oracle A1 | **Keep** as primary $0 host; live provision is operator-owned. Fallback: Hetzner CAX11, same Compose. aarch64 deps pre-checked. |

Toolchain pins found while scaffolding: TypeScript is held at ~5.9 (7.x is out but `vue-tsc` support is not assumed); ESLint 10 (required by `@nuxt/eslint` 1.17); Vitest 5; Vite 8.

## 2. Why Python (and not Go, .NET, NestJS, Rust, Laravel, Rails, Elixir)

The priority order was (1) best at the features and (2) a new language to learn. Python wins (1) decisively and is new for this portfolio (all other Kame apps are TS-first except kame-desk's API).

| Feature need | Python | Go | .NET | NestJS (TS) | Rust | Laravel / Rails | Elixir/Phoenix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Browser automation (Playwright) | ✅ official | ⚠️ community port | ✅ official | ✅ official | ❌ immature | ❌ | ❌ |
| LLM browser agents (browser-use, etc.) | ✅ richest | ❌ | ❌ | ⚠️ Stagehand | ❌ | ❌ | ❌ |
| AI/agents (PydanticAI, typed outputs) | ✅ | ⚠️ | ⚠️ Semantic Kernel | ✅ Vercel AI SDK | ⚠️ | ⚠️ | ⚠️ |
| Job scraping libs (JobSpy, extruct, Crawl4AI) | ✅ | ⚠️ (Colly is great for raw crawling) | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| Resume parse/render (docling, RenderCV) | ✅ | ❌ | ⚠️ | ⚠️ | ⚠️ Typst native | ❌ | ❌ |
| ML (scam classifier, embeddings) | ✅ | ❌ | ⚠️ ML.NET | ⚠️ | ⚠️ | ❌ | ⚠️ Nx |
| Durable human-in-the-loop workflows | ✅ DBOS/Temporal/Hatchet | ✅ Temporal | ✅ Temporal | ✅ Temporal | ⚠️ | ⚠️ queues | ✅ Oban |
| Reuse existing Kame tooling | ✅ kame-desk | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |

**Runner-up worth knowing:** Elixir/Phoenix (LiveView + Oban is lovely for realtime dashboards and schedules), but browser automation and AI tooling would need a Python sidecar anyway. **Go** is a great fit only for a raw high-volume crawler; httpx async in Python handles our polling volume (tens of thousands of boards, mostly cached) fine. If a hot path ever needs it, a Go crawler service can be added behind the same queue without changing anything else.

## 2a. Why Vue + Nuxt for the frontend (and not React, Svelte, or Angular)

Constraint from the owner: not React (most Kame apps are React/TanStack). kame-lends already uses SvelteKit, so Svelte isn't new either.

| Need | Vue 3 + Nuxt 4 | Angular 21 | SolidStart / Qwik |
| --- | --- | --- | --- |
| Share one component library between web app **and** browser extension | ✅ WXT has first-class Vue support; small side-panel bundles | ⚠️ Angular in an MV3 side panel is heavy and unusual | ⚠️ Solid works in WXT; small ecosystem |
| Dense, form-heavy, data-heavy SaaS UI | ✅ Reka UI, TanStack Table/Query (Vue), VeeValidate, VueUse, ECharts | ✅ Excellent (CDK, typed forms; Signal Forms still experimental in v21) | ⚠️ Fewer mature libraries |
| Realtime (SSE/WS), canvas live view | ✅ | ✅ | ✅ |
| Typed client from our FastAPI OpenAPI | ✅ Hey API / Orval vue-query | ✅ Angular HttpClient generators | ⚠️ |
| AI-agent coding support (docs, skills, model familiarity) | ✅ Strong; community Nuxt skills exist (e.g. `onmax/nuxt-skills`, vet before installing) | ✅ Strong | ⚠️ Weaker |
| Learning value vs React | High (SFCs, Composition API, reactivity model, Nuxt modules) | Very high (DI, RxJS/signals, opinionated architecture) | Medium (JSX like React) |
| Free hosting as static SPA | ✅ Cloudflare Pages | ✅ | ✅ |

**Decision: Vue 3.5 + Nuxt 4.** The deciding factor is the web/extension shared UI; Nuxt adds file routing, layouts, route middleware (auth/workspace guards), `@nuxt/icon`, `@nuxtjs/i18n`, PWA, and fonts with little config. Angular is the strong runner-up and would be the pick if the extension weren't core. Nuxt runs in SPA mode for the authenticated app (no SSR needed behind login), with prerendered public pages; business logic stays in FastAPI.

## 3. Why DBOS for workflows 🔬

The apply flow needs to: run a 30-step form fill, **pause for hours** waiting for a human (CAPTCHA, login, answer approval), survive restarts, then **resume exactly where it stopped**. Discovery needs cron schedules per Track and per-host rate limits.

| Option | Verdict |
| --- | --- |
| **DBOS Transact** | Library (not a server). Workflows and steps checkpointed in our Postgres; `recv`/`send` (or events) for human input with timeouts; scheduled workflows (cron); queues with concurrency + rate limits. Free, MIT. **Chosen.** |
| Temporal (self-hosted) | Gold standard, but a separate cluster (server + DB + UI) to run on a free VM. Overkill now. Swap path exists if needed. |
| Hatchet | Good, Postgres-based, but another service to run. |
| ARQ + Redis (kame-desk) | Not durable mid-workflow; we'd hand-roll checkpointing. |

Phase 1 spike: prove pause → restart process → resume, a cron schedule, and a rate-limited queue on the free VM. If DBOS fails the spike, fall back to Hatchet.

## 4. Repository layout (target)

```
kame-apply/
├─ apps/
│  ├─ web/          Vue 3 + Nuxt 4, SPA app + prerendered public pages (UI only)
│  ├─ api/          FastAPI (all business logic, DBOS workflows, WebSockets/SSE)
│  ├─ runner/       Playwright apply runner + live-view relay (separate container; can run on the user's machine)
│  └─ extension/    WXT browser extension (side panel, autofill, clipper)
├─ packages/
│  ├─ ui/           "Signal" design tokens + Vue components on Reka UI (web + extension)
│  ├─ api-client/   Hey API–generated TS client + TanStack Vue Query options
│  └─ py-core/      shared Python: models, schemas, source adapters, ATS adapters, AI prompts
├─ infra/           docker-compose (dev + prod), Caddy, backups
├─ docs/
└─ scripts/
```

## 5. Hosting plan (free first)

| Piece | Where | Cost |
| --- | --- | --- |
| Web app (static SPA/SSR shell) | Cloudflare Pages | $0 |
| API + DBOS workers + Postgres + runner + Caddy | **Oracle Cloud Always Free Ampere A1**, Docker Compose | $0 |
| Files | Cloudflare R2 | $0 (≤10 GB) |
| Inbound email | Cloudflare Email Routing + Worker | $0 |
| Outbound email | Resend | $0 (free tier) |
| Errors | Sentry | $0 |
| Dev database branches | Neon free (optional) | $0 |
| LLM | User's BYO key / Gemini free tier / Groq free tier / OpenRouter free models / Ollama local | $0 to user's budget |
| Backups | `pg_dump` nightly → R2 | $0 |

**Caveats:**

- Oracle reportedly **halved** the Always Free A1 allowance to **2 OCPU / 12 GB** in June 2026 (from 4/24), and some regions lack capacity. 2/12 still fits Postgres + API + workers + 1–2 concurrent headless Chromium sessions. Verify the allowance in the console during Phase 1.
- Fallback if Oracle is unavailable: Hetzner CAX11/CX22 (~€4–6/month), the only paid line item, same Compose file.
- **Local runner mode:** the `runner` container can run on the user's own machine and connect to the hosted API. This adds browser capacity for free, and the user's home IP and real browser get far fewer challenges than a datacenter IP.

## 5a. Why not Vercel or Supabase (considered first, as requested)

- **Vercel (free):** great for the web app, but serverless functions have short execution limits and can't run long Playwright sessions, durable multi-hour workflows, or WebSocket relays. The web app could live on Vercel; Cloudflare Pages is chosen because R2, Email Routing, and Workers sit on the same account. Either works for `apps/web`.
- **Supabase (free):** Postgres + Auth are good, but the free tier pauses projects after a week of inactivity and caps the DB at 500 MB (job text grows fast). Our backend is Python, so Supabase's main advantages (client SDK, RLS-from-browser, Edge Functions) go unused. We keep RLS in our own Postgres. Neon free stays the option for dev branches.

## 5b. LLM data-use note

Some providers' **free** API tiers may use inputs to improve their models. Resumes are personal data. The AI settings page shows each provider's data-use note, and users can block free tiers for personal-data features (profile, tailoring, answers) while keeping them for public job data (qualification extraction, scam checks). Local Ollama is the fully private option.

## 6. Explicitly out of scope

- React (incl. Next.js, TanStack Start), shadcn/ui, Lucide, and reuse of other Kame apps' design tokens/components, so Kame Apply keeps its own identity. (React appearing on employer forms the runner fills is unrelated.)
- tRPC, Supabase-as-BaaS, Prisma/Drizzle (TS ORMs don't apply; SQLAlchemy owns the DB), MongoDB, Redis (unless a spike proves DBOS insufficient), Kubernetes.
- Any anti-detection tooling: `playwright-stealth`, `undetected-chromedriver`, `camoufox` used for evasion, CAPTCHA solver SDKs, proxy rotators. See [`research/02 §5`](./research/02-job-discovery-and-site-access.md#5-the-bypass-question).
- AGPL dependencies in the hosted service (ApplyPilot, Skyvern core, OpenResume, PyMuPDF) unless we accept open-sourcing the service.
