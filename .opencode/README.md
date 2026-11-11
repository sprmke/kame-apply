# OpenCode — Kame Apply

Project-scoped OpenCode setup that matches Cursor, Claude Code, and Codex.

## Setup

```bash
pnpm install
pnpm run setup:ai-tooling
```

Then run `opencode` from the repo root. Personal providers and models stay in `~/.config/opencode/opencode.json`.

## What maps where

| Concern      | Canonical source                     | OpenCode path                             |
| ------------ | ------------------------------------ | ----------------------------------------- |
| Instructions | `AGENTS.md`                          | Auto-discovered (V2 reads AGENTS.md only) |
| Rules        | always-on `.cursor/rules/*.mdc`      | `opencode.json` → `instructions`          |
| Skills       | `.agent/skills/` + `.agents/skills/` | `opencode.json` → `skills` array          |
| Commands     | `.claude/commands/`                  | `.opencode/commands/` symlinks            |
| Subagents    | `.claude/agents/`                    | `.opencode/agents/` (V2 frontmatter)      |
| Guards       | `.claude/hooks/` (Cursor/Claude)     | `opencode.json` → `permissions` array     |
| MCP          | `.mcp.json`                          | `opencode.json` → `mcp.servers`           |

## Guards

OpenCode V2 enforces through config:

- `apps/api/migrations/versions/**` edits denied.
- Prod deploy, prod migration, and prod rollback denied; a command containing `applywave` is allowed.
- `.env.production*` edits denied.
- `rm -rf /` and `rm -rf ~` denied; `drop table` and force-push ask.
- Reads and edits outside the project ask, except the shared global skill library.

`.opencode/plugins/ka-ai-tooling.ts` targets the OpenCode V1 plugin API. V1 plugin
implementations do not run in V2, so treat it as legacy. The guarantees above live
in `opencode.json`.

## Token discipline

OpenCode sees project skills plus the five curated global behaviour skills. The
machine library at `~/.agents/skill-library` is not loaded directly; use
`agent-skills-index` to read a skill by path when a task needs it.

## Checks

```bash
pnpm run check:ai-tooling-sync
opencode debug config
opencode debug agents
```

Index: `.cursor/rules/README.md` · `.claude/README.md` · `AGENTS.md`.
