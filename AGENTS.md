# AGENTS.md

Guidance for Codex in this repository. Cursor and OpenCode read it too (`.cursor/rules/README.md`, `.opencode/README.md`); it is the single always-loaded agent context.

## What this is

**Kame Apply**: a multi-tenant web app that finds real, relevant jobs worldwide on a schedule, scores and safety-checks them, strengthens the user's resume with evidence from live postings, tailors each application, and helps apply faster. The human stays in control of anything that matters (logins, CAPTCHAs, sensitive data, and by default the final Submit). Core loop: **Track** (a role search) → discover → match → safety score → tailor → apply (assist) → track.

Authoritative docs: scope **`docs/prd.md`**, stack **`docs/tech-stack.md`**, build plan **`docs/phases/README.md`** (read the current phase file before any work), system **`docs/architecture/overview.md`**, design **`docs/design/design-system.md`**. Status: eng phases 0–20 complete (operator leftovers in `docs/phases/REMAINING.md`; open engineering gaps in `docs/reviews/full-review-phases-0-20.md`).

Stack: pnpm + Turborepo (TS) and uv workspace (Python). `apps/web` Vue 3 + Nuxt 4 SPA · `apps/api` FastAPI + SQLAlchemy 2 + Alembic + **DBOS** + PydanticAI (owns all business logic) · `apps/runner` Playwright · `apps/extension` WXT + Vue · `packages/{ui,api-client,py-core}`. Postgres 17 + pgvector + pg_trgm + **RLS**. Cloudflare R2, Resend. No Redis, Supabase, Prisma/Drizzle, tRPC, or React.

## Non-negotiable rules (PRD P1–P7)

1. **Truthful (P1)**: generated resumes/letters/answers use only Career Profile facts, each claim with an evidence ref; gaps stay gaps. `truthful-content.mdc`
2. **No evasion (P2)**: never add stealth plugins, CAPTCHA solvers, proxy rotation, fingerprint spoofing, or "humanized" input. A challenge pauses the run for the human. `job-site-access.mdc`
3. **User owns irreversible steps (P3)**: AI fills, the user clicks Submit. Never submit unless `policy.allow_submit`; never auto-submit on LinkedIn/Indeed/JobStreet. `apply-engine.mdc`
4. **Warn, don't block (P4)**: risk is a level with reasons; only sensitive-data fields hard-stop. `pii-guard.mdc`
5. **Respect the source (P5)**: official APIs/feeds first, polite fetching, link back, never republish. A block signal disables the source.
6. **Untrusted input is data (P6)**: postings, emails, pages are delimited data to tool-less LLM calls, never instructions. `untrusted-content.mdc`
7. **Free to run (P7)**: core features work on free tiers or self-hosted software.

Also: never accept, store, or relay a user's Claude.ai credentials server-side (`docs/research/08-bring-your-own-AGENTS.md`).

## Architecture invariants (`docs/architecture/overview.md` §1)

1. FastAPI owns all business logic; web and extension are UI only.
2. Every tenant row has `workspace_id` + RLS; every request/step sets `app.workspace_id`. No query path without scope; never trust a client `workspace_id`. `workspace-scoping.mdc`
3. AI output is a **draft** until the user accepts it.
4. Untrusted text is sanitized and passed only as delimited data.
5. Every mutation writes an append-only `activity_log` row (or `activity-log: N/A — <why>`). `audit-logging.mdc`
6. Blobs live in R2 by key, never in Postgres.
7. A run continues past a checkpoint only after a recorded human decision. Checkpoint kinds: `login`, `captcha`, `ai_restricted`, `sensitive_field`, `unknown_required`, `answer_approval`, `risk`, `final_review`, `blocked`.

## Commands

```bash
pnpm install && uv sync --all-packages   # once; then: pnpm run setup:ai-tooling
pnpm run dev:docker               # Postgres+pgvector (5442), MinIO (9100/9101), Mailpit (1125/8125)
pnpm run dev                      # migrate, then API (8100) + web (3100) together (./dev.sh)
pnpm run dev:api / dev:web        # one side only
pnpm run stop:docker

pnpm run lint / lint:fix / format / format:check / type-check / build
pnpm run test                     # pytest (apps/api, needs dev:docker) + Vitest (web, ui, extension)
pnpm run test:api / test:web
pnpm run gen:api-client           # OpenAPI -> packages/api-client; check:api-client = CI drift check
pnpm run ci:quality               # everything CI runs, run before every PR

pnpm run db:migrate / db:migrate:new -- "msg" / db:reset:local / db:seed
pnpm run check:ai-tooling-sync / check:filenames / check:stack-terminology / check:hooks
pnpm run env:status
pnpm run deploy:*:prod / migrate:prod / backup:db:* / restore:drill:local  # Phase 14; prod needs unlock word
```

Use `uv run` for all Python (`uv run pytest apps/api -q`, `uv run alembic ...` from `apps/api`). Local ports: web 3100, API 8100, Postgres 5442. Gotchas: the compose init SQL runs only on a fresh volume (see `docs/architecture/deployment.md`); `apps/api` tests use the `kame_apply_test` DB and reset the schema each session; keep `typescript` at ~5.9 until `vue-tsc` support is confirmed.

## Build loop (every phase; `docs/research/06-agentic-workflow.md` §3)

`/ka-start-work phase-NN` → scratchpad in `docs/workflow/in-progress/` → branch `phase/NN-<slug>` → vertical slices (test first where practical, UI checked at 375/820/1440, docs in the same change, evals for AI changes) → `/ka-check-before-pr` (`ci:quality`, `verifier`, `security-auditor`/`design-reviewer` as applicable) → `/ka-submit-for-review` (PR with exit-criteria checklist, status table updated). A phase is done only when exit criteria are checked, acceptance scenarios pass in the running app, empty/loading/error states exist, docs are updated, and no new lint/type errors remain.

## Conventions

- **Naming**: Python `snake_case.py`, `PascalCase` models, schemas suffixed by intent (`TrackCreate/Read/Update`); Vue `PascalCase.vue`, composables `useX.ts`, other TS `kebab-case.ts`. `naming-conventions.mdc`
- **Secrets**: `apps/api/.env` (gitignored); never commit or log credentials, tokens, or sensitive values.
- **Migrations**: Alembic only; never edit a shipped one. `migrations.mdc`
- **Time**: timestamps UTC in the DB; display in the user's timezone.
- **Copy**: minimal UI text (`ui-minimal-copy.mdc`); short, plain, no AI tells, no em dashes (`human-copy.mdc`).
- **Design**: Field Notes only (paper/ink + persimmon, Instrument Sans / Newsreader / Martian Mono, Phosphor, Reka UI). Never reuse another Kame app's tokens, components, or look. `anti-slop-design.mdc`
- **Testing**: pytest + httpx (API), Vitest (web), Playwright E2E, evals for AI; tests ship with the phase that introduces the surface, including a cross-tenant test for every new tenant table.

## AI session hygiene

`.cursor/rules/ai-usage.mdc`: one task per session (`/clear` between goals), no subagent swarms by default, medium effort for routine work, high effort for architecture, RLS, safety, apply engine, and prompt design. Heavy rules are glob-scoped; read them when you touch that surface. Use `context7` for library docs (needs `/mcp` authorization in an interactive session).

## Plan mode

Planning without implementing: write no code, save the plan to `docs/workflow/planned/<slug>.md` (no date prefix) and add a row to `docs/workflow/planned/README.md`. `plan-mode.mdc`

## Docs are the source of truth

When you implement or materially change behavior (features, routes, validation, API, schema, env vars, integrations, AI features, user-visible flows), update docs **in the same change**.

| Change                                          | Update                                                            |
| ----------------------------------------------- | ----------------------------------------------------------------- |
| Architecture, API surface, data model, env vars | `docs/architecture/*.md`                                          |
| Page/section behavior, save flows, validation   | `docs/guides/routes/*.md` (`route-guides`)                        |
| Product scope                                   | `docs/prd.md`                                                     |
| Workflow/checkpoint behavior                    | `docs/architecture/overview.md` §3 + the phase file               |
| AI feature or agent tool                        | the owning phase file (+ `docs/phases/phase-12b-*` for MCP tools) |
| Mutation                                        | `activity_log` event or `activity-log: N/A — <why>`               |
| Migration/backfill                              | `docs/architecture/deployment.md`                                 |
| Phase progress                                  | phase file checklist + `docs/phases/README.md` status table       |
| Rules agents rely on                            | this file, if the old text would mislead                          |

Trivial fixes (typos, behavior-neutral renames) need no doc change. Index: `.cursor/rules/README.md` · `.codex/README.md` · `.opencode/README.md`.

## Agent tooling

Skills in `.agent/skills/` (canonical; symlinked into `.agents/skills/` and `.cursor/skills/`; index in `.agent/skills/README.md`). Subagents: `debugger`, `security-auditor`, `test-runner`, `verifier`, `design-reviewer`. Commands: `/ka-*` (start with `/ka-help`) and `/workflow-*`. MCP: `context7`, `markitdown`, `playwright`, `postgres` (local read-only role only; `.mcp.json`). Hooks: shell guard, shipped-migration guard, formatter, stack/evasion check, docs-sync reminders. Superpowers is **opt-in only** (`superpowers-opt-in.mdc`).

## Don'ts

- Any evasion tooling (see rule 2); scraping logged-in pages of platforms whose terms forbid it.
- React/Next.js/TanStack Start/shadcn/Lucide, Supabase, Prisma/Drizzle, tRPC, Redis/ARQ in our own code (`docs/tech-stack.md` §6). Employer-form adapters may mention React widgets as the target.
- Business logic in Nuxt server routes or the extension; side effects inline in a router instead of a service.
- Editing a shipped Alembic migration.
- Fabricated resume content; AI output written as final without user acceptance.
- Sensitive-class values in the profile, logs, prompts, or fixtures.
- **Production deploys or migrations without unlock**: never run or recommend `deploy:*:prod`, `migrate:prod`, or any write against a hosted `DATABASE_URL` unless the user said **`applywave`** in the same message (`no-prod-deploy.mdc`; the shell hook enforces it).
- AI attribution in commits or PR text (`git-commits.mdc`).

## Codex compatibility

Before working, read [.codex/README.md](.codex/README.md). It lists this project’s always-on Cursor rules and scoped rules to read for the affected files. Codex skills are discovered in `.agents/skills`; specialist definitions are in `.codex/agents`. Existing Cursor/Claude model aliases are not Codex model settings. Use available Codex tools and preserve project-specific architecture and authorization rules.

Superpowers workflows and subagent delegation remain opt-in; do not start them automatically. Run `python3 .codex/sync.py` after changing project skills, commands or agent definitions. Review/trust hooks through Codex before relying on their enforcement. This repository setup is independent of the hourly job-search task in the personal chat.

<!-- global-agent-skills -->

## Global agent skills

This machine has 159 shared skills in `~/.agents/skill-library` (Claude Code, Cursor,
Codex and OpenCode all read them). Only five behaviour skills are always visible.
For anything else, open `~/.agents/skill-library/agent-skills-index/SKILL.md`, find the
skill that fits, then read `~/.agents/skill-library/<skill>/SKILL.md`.
Manage with `~/.agents/bin/agent-stack.sh`. Repo skills and rules always win.
