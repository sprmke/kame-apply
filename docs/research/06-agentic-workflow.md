# Research 06: Agentic coding workflow for building Kame Apply

**Researched:** 2026-10-28 (surveyed `../kame-desk`, `../kame-homes`, `../kame-lends`, `../kame-finance`, `../kame-hunt`, `../kame-pick`). Implemented in **Phase 0**.

## 1. What to reuse (and from where)

`kame-desk` is the closest **backend** match (FastAPI + SQLAlchemy/Alembic + pnpm/Turbo + uv) and already ported kame-homes' tooling, so it's the primary source for process and backend tooling. The **frontend is new** (Vue 3 + Nuxt 4, Field Notes design system), so React/TanStack-Start and design-specific items are **rewritten, not ported**. Same layout: canonical skills in `.agent/skills/`, symlinked into `.claude/skills/` and `.cursor/skills/`; Cursor rules in `.cursor/rules/*.mdc`; Claude hooks in `.claude/hooks/` registered in `.claude/settings.json`; OpenCode mirror in `.opencode/` + `opencode.json`; MCP in `.mcp.json`; sync/drift scripts in `scripts/dev/`.

### Port as-is (rename prefixes `dd-` → `ka-`, DoctorDesk → Kame Apply)

| Kind | Items (source: kame-desk unless noted) |
| --- | --- |
| Rules (`.cursor/rules/`) | `ai-usage`, `documentation-maintenance`, `git-commits` (no AI attribution), `human-copy`, `ui-minimal-copy`, `anti-slop-design`, `naming-conventions`, `no-prod-deploy` (unlock word: **`applywave`**), `plan-mode`, `self-review`, `security`, `migrations`, `superpowers-opt-in`, `fastapi-conventions`, `route-guides`, `audit-logging`, `in-app-notifications` (backend half), `markitdown-mcp`, `workflow-docs`; `anti-slop-design` keeps its structure but its banned list is rewritten for Field Notes (design-system §13) |
| Skills (`.agent/skills/`) | `fastapi-stack`, `alembic-migrations`, `fastapi-jwt-auth`, `rbac-and-audit`, `audit-logging`, `pgvector-chart-search` → `pgvector-search`, `pdf-generation` (adapt to RenderCV), `documentation-maintenance`, `route-guides`, `fix-migration-issues`; from kame-homes: `multi-tenancy`, `human-copy`, `minimal-ui-copy`, `accessibility` (framework-agnostic parts), `production-readiness-review`, `gmail-listener` (Phase 17), `workflow`, `workflow-intake-scratchpads`, `karpathy-guidelines`, `self-review`, `git-commits`, `docs-first` |
| **Rewrite for Vue/Nuxt + Field Notes** (don't port; React/shadcn-specific) | Rules: `nuxt-conventions` (SPA app routes, middleware for auth/workspace, composables, no business logic in the client), `vue-components` (SFC + `<script setup lang="ts">`, props/emits typing, Reka UI wrapping, `tailwind-variants`), `field-notes-design` (tokens, signature components, do/don't), `mobile-responsive` (Reader/Workbench breakpoints), `motion` (steady pace tokens, `motion-v`). Skills: `vue-query-data` (Hey API options + `computed` params, invalidation, optimistic updates), `vee-validate-forms` (Zod schemas, unsaved-changes guard), `tanstack-table-vue` (virtualized Reader lists), `field-notes-components` (how to build/extend proof mark, pencil text, route line...), `design-review` (Field Notes checklist + screenshots). |
| Adapt | `clinic-scoping` → **`workspace-scoping`** (RLS + dependency), `ai-clinic-assistant` → **`ai-features`** (draft-then-confirm, tiers, budget), `arq-background-jobs` → replaced by **`dbos-workflows`** |
| Agents | `debugger`, `security-auditor`, `test-runner`, `verifier`, `design-reviewer` (Claude + Cursor + OpenCode flavors) |
| Hooks | `guard-shell` (blocks prod deploy/migrate without unlock, `rm -rf` outside repo, secrets in git), `guard-shipped-migrations`, `format-edited-file` (ruff + prettier), `check-stack-terminology` (flags React/Next.js/TanStack Start/shadcn/Lucide/Supabase/Drizzle/ARQ drift in our own code; employer-form adapters may mention React widgets), `session-docs-sync-reminder`, `remind-docs-on-code-edit`, `session-ai-tooling-sync`, `session-superpowers-opt-in` + `superpowers-lean-mode`, `session-workflow-in-progress` |
| Commands | `/ka-help`, `/ka-start-work`, `/ka-start-app`, `/ka-check-before-pr`, `/ka-submit-for-review`, `/ka-pull-new-changes`, `/ka-create-new-ticket`, `/ka-design-review`, workflow trio (`workflow-start/done/sync-scratchpads/wont-do` from kame-lends) |
| Scripts | `setup-ai-tooling.sh`, `check-ai-tooling-sync.sh`, `check-filename-conventions.sh`, `ci-quality-gate.sh`, `capture-design-screenshots` (375/820/1440 × light/dark) |
| MCP | `context7` (library docs), `markitdown` (read uploaded docs), `playwright` (UI verification), `postgres` (local dev DB only) |
| Design | Only the **pattern** of `DESIGN.md` + `PRODUCT.md` + `.impeccable/` from kame-homes. Content is new, from [`design/design-system.md`](../design/design-system.md); never copy other Kame apps' tokens, fonts, icons, or components |

### New, domain-specific for Kame Apply (write in Phase 0, refine in the phase that uses them)

| Rule / skill | Content |
| --- | --- |
| `job-site-access.mdc` (always on) | PRD P2/P5 + research/02 §5–6: no evasion tooling, politeness checklist, ToS-restricted platforms list, block ⇒ disable. `check-stack-terminology` hook also greps for `playwright-stealth`, `undetected`, `capsolver`, `2captcha`, proxy-rotation libs and fails. |
| `truthful-content.mdc` (always on for `resumes/`, `answers/`) | P1 + research/05 §1: evidence refs, verifier, gaps not insertions. |
| `untrusted-content.mdc` | P6 + research/04 §4. |
| `pii-guard.mdc` | Sensitivity classes, redaction, never store sensitive values. |
| `apply-engine.mdc` | Page loop, checkpoint kinds, "never click submit unless policy.allow_submit", step logging. |
| skill `source-adapter` | How to add a job source: interface, normalization, terms note, rate limits, fixtures, health metrics, tests. |
| skill `ats-adapter` | How to add an ATS form adapter: detection, step model, field map, widgets, fixtures from saved HTML, checkpoint triggers. |
| skill `dbos-workflows` | Workflow/step design, idempotency, `recv`/`send` checkpoints, schedules, queues, testing workflows. |
| skill `pydantic-ai-features` | Prompt registry, structured outputs, provider router, budgets, SSE streaming, eval suite. |
| skill `ai-evals` | Golden sets, fabrication checks, how to add an eval when changing a prompt. |
| skill `wxt-extension` | WXT structure, messaging, permissions, content-script patterns, store packaging. |
| skill `live-view` | CDP screencast relay and takeover protocol. |

## 2. External skills to install (via `npx skills add`, pinned in `skills-lock.json`)

Already proven in kame-homes' lock:

- `anthropics/skills`: `claude-api`, `webapp-testing`, `pdf`, `docx`, `mcp-builder`, `skill-creator`
- `mattpocock/skills`: `tdd`, `to-spec`, `to-tickets`, `grill-me`, `diagnosing-bugs`, `implement`, `improve-codebase-architecture`
- `obra/superpowers`: **opt-in only** (global rule): `brainstorming`, `writing-plans`, `executing-plans`, `systematic-debugging`, `verification-before-completion`
- Design (framework-agnostic): `impeccable`, `ui-ux-pro-max`, `frontend-design`, `web-design-guidelines`. **Not** the React-specific `vercel-react-*` skills.
- Vue/Nuxt: search with `find-skills` / skills.sh (e.g. community `onmax/nuxt-skills` covering Nuxt, Vue, Nuxt UI, VueUse); install only after reading, and drop parts that assume Nuxt UI's default look
- Testing/browser: `playwright-cli`, `webapp-testing`
- Security: `security-audit`

Before installing any third-party skill: read it fully (skills are code-adjacent instructions), pin by hash, and note why it's included in `.agent/skills/README.md`.

## 3. The build loop (every phase)

```
/ka-start-work phase-NN
  1. Read docs/phases/README.md → phase-NN file → linked docs only. (One phase ≈ one or a few sessions; /clear between goals.)
  2. Create docs/workflow/in-progress/phase-NN-<slug>.md scratchpad: plan of vertical slices, open questions, decisions.
  3. Branch: phase/NN-<slug>.
  4. For each slice: test first where practical (pytest / Vitest) → implement → run targeted tests → UI check via
     Playwright MCP at 375/820/1440 → update docs (route guide, architecture) in the same change.
  5. AI features: add/extend eval cases; run `pnpm run test:evals`.
/ka-check-before-pr
  6. pnpm run ci:quality (lint, types, filenames, build, tests, tooling-sync, stack-terminology, evals-lite)
  7. verifier agent: walks the phase's exit criteria + acceptance scenarios against the running app; security-auditor
     for auth/tenancy/PII-touching phases; design-reviewer for UI phases.
/ka-submit-for-review
  8. PR with exit-criteria checklist; update docs/phases/README.md status; move scratchpad to docs/workflow/done/.
```

**Model/effort routing:** routine CRUD/UI slices at medium effort; architecture, tenancy/RLS, safety, apply engine, and prompt design at high effort. Subagents only when asked or clearly useful (kame-desk `ai-usage` rule).

**Definition of Done (every phase):** exit criteria checked; acceptance scenarios pass in the running app (not just tests); mobile + desktop screenshots reviewed; empty/loading/error states present; docs updated; activity log events emitted for mutations; no new lint/type errors; evals pass for touched AI features.

## 4. Configuration for the three agents

- **Claude Code:** `CLAUDE.md` (single always-loaded context), `.claude/settings.json` hooks + permissions (allow: `uv run`, `pnpm`, read-only git; ask: deploys, migrations; deny: prod unlock-less commands), agents, commands, skills symlinks.
- **Cursor:** `.cursor/rules` (glob-scoped heavy rules), `.cursor/hooks.json`, `.cursor/skills`, `.cursor/mcp.json`.
- **OpenCode:** `opencode.json`, `.opencode/agents`, `.opencode/commands`, `.opencode/plugins/ka-ai-tooling.ts` (port of `dd-ai-tooling.ts`).
- `check-ai-tooling-sync.sh` enforces parity in CI.

Note: in this environment the `context7` MCP plugin currently needs authorization (`/mcp` in an interactive session) before agents can use it.
