# Cursor rules: Kame Apply

After clone: `pnpm run setup:ai-tooling`. Claude Code and OpenCode read the same rules through `CLAUDE.md` and `opencode.json`.

## Always-on

| Rule | Purpose |
| --- | --- |
| `project-context.mdc` | Stack + where to edit |
| `ai-usage.mdc` | Session hygiene, model routing |
| `documentation-maintenance.mdc` | Docs sync |
| `ui-minimal-copy.mdc` / `human-copy.mdc` | Copy policy |
| `no-prod-deploy.mdc` | Prod guard (unlock: **applywave**) |
| `job-site-access.mdc` | No evasion tooling, politeness (P2/P5) |
| `pii-guard.mdc` | Sensitivity classes, never store sensitive values |
| `workspace-scoping.mdc` | `workspace_id` + RLS everywhere |
| `audit-logging.mdc` | `activity_log` on mutations |
| `route-guides.mdc` | Per-route docs |
| `superpowers-opt-in.mdc` | Superpowers opt-in |
| `git-commits.mdc` | No AI attribution |
| `markitdown-mcp.mdc` | PDF/Office via MCP |

## Glob-scoped (read when touching that surface)

| Rule | Surface |
| --- | --- |
| `truthful-content.mdc` | resumes, answers, profiles, AI prompts (P1) |
| `untrusted-content.mdc` | jobs, safety, ingest, runs, runner, extension (P6) |
| `apply-engine.mdc` | sources, runs, runner, extension |
| `dbos-workflows.mdc` | `**/workflows.py` |
| `pydantic-ai.mdc` | `app/ai/**`, prompts |
| `fastapi-conventions.mdc` · `migrations.mdc` · `security.mdc` | `apps/api/**` |
| `nuxt-conventions.mdc` · `vue-components.mdc` | `apps/web`, `apps/extension`, `packages/ui` |
| `signal-design.mdc` · `anti-slop-design.mdc` · `mobile-responsive.mdc` · `motion.mdc` | UI |
| `naming-conventions.mdc` · `in-app-notifications.mdc` | as globbed |
| `plan-mode.mdc` · `workflow-docs.mdc` · `self-review.mdc` | process (opt-in) |

Skills: `.agent/skills/` (symlinked into `.claude/skills` and `.cursor/skills`; index in `.agent/skills/README.md`). Commands: `/ka-help`. Subagents: `debugger`, `security-auditor`, `test-runner`, `verifier`, `design-reviewer`. OpenCode: `.opencode/README.md`.
