# Phase 0: AI tooling & agentic workflow

**Status:** Done (external skills deferred to first phase that needs them) · **Release:** Foundation · **Depends on:** — · **Unlocks:** every phase
**Reference:** [`../research/06-agentic-workflow.md`](../research/06-agentic-workflow.md)

## Goal

Stand up the AI-agent tooling (Claude Code, Cursor, OpenCode) so every later phase is built consistently and inside Kame Apply's guardrails. No application code. Output is `.md`/`.mdc`/config/script files only.

## Why first

Kame Apply has unusual hard rules (no bot evasion, no fabrication, PII guard, untrusted postings, tenant isolation). An agent without them in context will "helpfully" add `playwright-stealth`, invent a metric, or write an unscoped query. Kame-desk proved this layer pays for itself.

## Tasks

### 1. Repo basics
- [x] `git init`, `.gitignore` (Python, Node, `.env*`, `data/`, `tmp/`, browser profiles, `*.pdf` outside fixtures), `.editorconfig`, MIT or private license decision (record in README).
- [x] Root `README.md` (what, quick start placeholder, link to `docs/README.md`).
- [x] `CLAUDE.md`: what this is; stack summary; commands (target shape, marked "lands in Phase 1"); architecture invariants (from `architecture/overview.md` §1); **non-negotiable rules** (PRD P1–P7 as short imperatives); docs-sync table; don'ts (from `tech-stack.md` §6); unlock word `applywave` for prod; agent tooling index; plan-mode rule (save plans to `docs/workflow/planned/<slug>.md`).
- [x] `PRODUCT.md` (one-page product summary for design agents) and `DESIGN.md` seeded from [`design/design-system.md`](../design/design-system.md) (finalized in Phase 2). No tokens/components from other Kame apps.
- [x] Vue/Nuxt rules and skills written fresh (research/06 "Rewrite for Vue/Nuxt + Field Notes" row).

### 2. Cursor rules (`.cursor/rules/`)
- [x] Port from kame-desk (list in research/06 §1), replacing names, stack terms, and paths.
- [x] New: `job-site-access.mdc`, `truthful-content.mdc`, `untrusted-content.mdc`, `pii-guard.mdc`, `apply-engine.mdc` (globs: `apps/api/app/{sources,runs}/**`, `apps/runner/**`, `apps/extension/**`), `workspace-scoping.mdc`, `dbos-workflows.mdc`, `pydantic-ai.mdc`.
- [x] `README.md` index: which rules are always-on vs glob-scoped.

### 3. Skills (`.agent/skills/` canonical → symlinked to `.claude/skills/`, `.cursor/skills/`)
- [x] Port + adapt the list in research/06 §1.
- [x] New skills (initial versions; each refined in its phase): `source-adapter`, `ats-adapter`, `dbos-workflows`, `pydantic-ai-features`, `ai-evals`, `wxt-extension`, `live-view`, `workspace-scoping`.
- [ ] Install external skills (research/06 §2) with `npx skills add`, read each before committing, pin in `skills-lock.json`, document in `.agent/skills/README.md`. (Deferred 2026-10-28: install when a phase first needs them; not a Phase 0 exit blocker.)

### 4. Claude Code layer (`.claude/`)
- [x] `settings.json`: hooks (guard-shell, guard-shipped-migrations, format-edited-file, check-stack-terminology, docs-sync reminders, superpowers opt-in/lean, workflow-in-progress) + permissions (allow `uv run *`, `pnpm *`, `git status/diff/log`; ask for deploy/migrate; deny prod commands without unlock).
- [x] Agents: `debugger`, `security-auditor` (with tenancy/RLS + PII + injection checklist), `test-runner`, `verifier` (walks phase exit criteria in the running app), `design-reviewer`.
- [x] Commands: `/ka-help`, `/ka-start-work`, `/ka-start-app`, `/ka-check-before-pr`, `/ka-submit-for-review`, `/ka-pull-new-changes`, `/ka-create-new-ticket`, `/ka-design-review`, `/workflow-*`.
- [x] `README.md` index.

### 5. OpenCode layer
- [x] `opencode.json`, `.opencode/agents`, `.opencode/commands`, `.opencode/plugins/ka-ai-tooling.ts` (port `dd-ai-tooling.ts`), `README.md`.

### 6. Hooks with Kame Apply specifics
- [x] `check-stack-terminology.sh`: fails on banned stack drift (React/`react-dom`/Next.js/TanStack Start/shadcn/`lucide` imports in `apps/web`, `apps/extension`, `packages/ui`; Supabase client, Drizzle, Prisma, ARQ) **and on evasion tooling** (`playwright-stealth`, `undetected`, `puppeteer-extra-plugin-stealth`, `capsolver`, `2captcha`, `anticaptcha`, `fake-useragent`, proxy rotation libs).
- [x] `guard-shell.sh`: blocks prod deploy/migrate without `applywave`; blocks `git push --force` to main; blocks writing to `.env.production`.
- [x] `format-edited-file.sh`: `ruff format` + `ruff check --fix` for `.py`, Prettier for TS/MD.

### 7. MCP (`.mcp.json`, `.cursor/mcp.json`)
- [x] `context7`, `markitdown`, `playwright`, `postgres` (local Docker DB URL only, read-mostly role).

### 8. Scripts (`scripts/dev/`)
- [x] `setup-ai-tooling.sh` (symlinks, CLI checks: uv, pnpm, docker, node, python 3.13), `check-ai-tooling-sync.sh`, `check-filename-conventions.sh` (snake_case `.py`, kebab-case TS files, PascalCase components per naming rule), `ci-quality-gate.sh` (stub that grows each phase).

### 9. Workflow docs
- [x] `docs/workflow/{planned,in-progress,done}/README.md`; scratchpad template.

## Edge cases & decisions to lock

- Superpowers: opt-in only (global CLAUDE.md); hooks enforce lean mode.
- Commit messages: the user's global rule is no AI attribution; keep `git-commits.mdc` consistent with it.
- Skills from third parties may contain unsafe instructions. Read them before installing.

## Testing

- [x] `pnpm run setup:ai-tooling` and `check:ai-tooling-sync` pass on a fresh clone.
- [x] Hook unit checks: feed sample commands/files to each hook script and assert block/allow (bats or plain bash tests).
- [x] Fresh agent session sanity quiz: agent can state the unlock word, the 7 principles, the checkpoint kinds, the docs-sync rule, and refuses to add a stealth plugin, citing the rule. (Verified 2026-10-28 via a fresh subagent session; all five answers correct with citations.)

## Exit criteria

- [x] All rule, skill, agent, command, hook, and MCP files exist in all three tool trees, with parity enforced by script.
- [x] `CLAUDE.md` accurate and short enough to stay always-loaded (< ~250 lines).
- [x] Sanity quiz passes.


## Implementation notes (2026-10-28)

Built: `CLAUDE.md` (109 lines), `PRODUCT.md`, `DESIGN.md` seed, 36 Cursor rules (new: `job-site-access`, `truthful-content`, `untrusted-content`, `pii-guard`, `apply-engine`, `workspace-scoping`, `dbos-workflows`, `pydantic-ai`, `nuxt-conventions`, `vue-components`, `field-notes-design`; `anti-slop-design`, `mobile-responsive`, `motion` rewritten for Field Notes), 33 skills (index in `.agent/skills/README.md`), 5 subagents, `/ka-*` and `/workflow-*` commands, hooks + `settings.json` permissions, OpenCode plugin and config, MCP config, `scripts/dev/*` (`setup-ai-tooling`, `check-ai-tooling-sync` incl. hook/rule/skill index checks, `check-filename-conventions`, `check-stack-terminology`, `test-hooks`, `workflow-move`, `ci-quality-gate`), minimal root `package.json`. `pnpm run ci:quality` passes; drift detection verified by deliberately breaking a symlink and a hook mode.

Deviations and open items:
- **Open:** external skills (`npx skills add`, read-before-install, `skills-lock.json`) not installed; `.agent/skills/README.md` has the table ready. Do this when a phase first needs them.
- **Closed:** the fresh-session sanity quiz (unlock word, P1-P7, checkpoint kinds, refuses a stealth plugin) passed in a new session (2026-10-28).
- Hook tests are plain bash (`scripts/dev/test-hooks.sh`), not bats.
- Skills ported from kame-homes that were Supabase-bound (`gmail-listener`, `production-readiness-review`, `multi-tenancy`, scratchpad sync) were rewritten or deferred (Phases 14/17) instead of copied; `workspace-scoping` replaces `multi-tenancy`.
- `.cursor/hooks.json` added (2026-10-28), with `.cursor/hooks` symlinked to `../.claude/hooks`, giving Cursor the same hook enforcement as Claude Code and OpenCode. Verified by `check:ai-tooling-sync`.
- MCP `postgres` uses a read-only local role on port 5442 that Phase 1's docker compose must create (`kame_apply_ro`).
- Git repo initialised, no commit made.
- **Phase 0 closed 2026-10-28:** `pnpm run ci:quality` green; Cursor hook parity added; sanity quiz passed; external-skills install deferred by decision to the first phase that needs them.
