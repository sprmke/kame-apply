# Codex project configuration

Root AGENTS.md is the entry point. Existing domain guidance remains in its original files. This file documents the compatibility layer, not application behavior.

## Rules

Codex does not automatically activate Cursor .mdc rules. Before work, read the always-on rules listed below. Read scoped rules when the task or files match their scope. Cursor model aliases and tool names are not Codex settings; use the current Codex model and available tools. Superpowers and delegation remain opt-in.

| Source rule | When to read |
|---|---|
| `.cursor/rules/ai-usage.mdc` | Always |
| `.cursor/rules/anti-slop-design.mdc` | - apps/web/**/*.vue |
| `.cursor/rules/apply-engine.mdc` | - apps/api/app/sources/** |
| `.cursor/rules/audit-logging.mdc` | Always |
| `.cursor/rules/dbos-workflows.mdc` | - apps/api/app/**/workflows.py |
| `.cursor/rules/documentation-maintenance.mdc` | Always |
| `.cursor/rules/fastapi-conventions.mdc` | - apps/api/** |
| `.cursor/rules/signal-design.mdc` | - apps/web/** |
| `.cursor/rules/git-commits.mdc` | Always |
| `.cursor/rules/human-copy.mdc` | Always |
| `.cursor/rules/in-app-notifications.mdc` | - apps/api/app/notifications/** |
| `.cursor/rules/job-site-access.mdc` | Always |
| `.cursor/rules/markitdown-mcp.mdc` | Always |
| `.cursor/rules/migrations.mdc` | - apps/api/migrations/** |
| `.cursor/rules/mobile-responsive.mdc` | - apps/web/** |
| `.cursor/rules/motion.mdc` | - apps/web/** |
| `.cursor/rules/naming-conventions.mdc` | - apps/** |
| `.cursor/rules/no-prod-deploy.mdc` | Always |
| `.cursor/rules/nuxt-conventions.mdc` | - apps/web/** |
| `.cursor/rules/pii-guard.mdc` | Always |
| `.cursor/rules/plan-mode.mdc` | Task-specific; read when relevant |
| `.cursor/rules/project-context.mdc` | Always |
| `.cursor/rules/pydantic-ai.mdc` | - apps/api/app/ai/** |
| `.cursor/rules/route-guides.mdc` | Always |
| `.cursor/rules/security.mdc` | - apps/api/app/core/** |
| `.cursor/rules/self-review.mdc` | Task-specific; read when relevant |
| `.cursor/rules/superpowers-opt-in.mdc` | Always |
| `.cursor/rules/truthful-content.mdc` | - apps/api/app/resumes/** |
| `.cursor/rules/ui-minimal-copy.mdc` | Always |
| `.cursor/rules/untrusted-content.mdc` | - apps/api/app/jobs/** |
| `.cursor/rules/vue-components.mdc` | - apps/web/**/*.vue |
| `.cursor/rules/workflow-docs.mdc` | Task-specific; read when relevant |
| `.cursor/rules/workspace-scoping.mdc` | Always |

## Skills and commands

Codex discovers the existing project skills through relative links under .agents/skills. Original folders and resources stay together so changes remain shared with Cursor/Claude. Do not move or copy only SKILL.md. Run `python3 .codex/sync.py` after adding or changing skills, commands or agent definitions.

Command adapters use `$source-command-<command>` and read the original command file; they do not automatically run on every task. See compatibility.json for exact names and sources. Native specialist definitions live in .codex/agents; use them only with explicit delegation requests.

## Hooks and connected tools

Existing command hooks are adapted to Codex event payloads. apply_patch file paths are extracted for migration guards and file reminders. Legacy ask decisions become a supported denial with the original reason because Codex does not support ask from PreToolUse yet. The adapter does not execute the proposed command. Review/trust project hooks in Codex before relying on them; this setup does not bypass trust. Shell commands that edit files remain subject to shell policy, not an absolute filesystem enforcement layer.

Existing .codex/config.toml MCP settings are preserved. Cursor MCP settings and editor extensions do not automatically become Codex integrations. Use connected Codex tools where available; per-server authentication and local service availability still apply. No production service or credentials are provisioned by this compatibility setup.

## Validation

Configuration validation checks skill metadata and links, original command references, TOML/JSON parsing and safe hook fixtures. It does not assert the application builds or that external MCP services are authenticated.

Skills available locally: 42. Command adapters: 11. Specialist definitions: 5.
