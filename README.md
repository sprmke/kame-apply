# Kame Apply

Find real jobs worldwide, strengthen your resume with live market evidence, tailor each application, and apply faster. You stay in control of the irreversible steps.

**Status:** planning docs complete; Phase 0 (AI tooling) built, Phase 1 (scaffold, CI, spikes) in progress. See [`docs/README.md`](docs/README.md) and the build plan in [`docs/phases/README.md`](docs/phases/README.md).

## Quick start

Needs Docker, Node (see `.nvmrc`), pnpm, uv, and `jq`.

```bash
pnpm install
uv sync --all-packages
cp apps/api/.env.example apps/api/.env
pnpm run setup:ai-tooling     # symlinks + CLI checks (agents)
pnpm run dev:docker           # Postgres, MinIO, Mailpit
pnpm run dev                  # migrate, API :8100, web :3100
```

Quality gate before a PR: `pnpm run ci:quality`. Commands and gotchas: `CLAUDE.md`; local environment: `docs/architecture/deployment.md`.

## Working with AI agents

`CLAUDE.md` is the always-loaded context. Rules, skills, subagents, commands, hooks, and MCP servers for Claude Code, Cursor, and OpenCode are indexed in [`.claude/README.md`](.claude/README.md), [`.cursor/rules/README.md`](.cursor/rules/README.md), and [`.opencode/README.md`](.opencode/README.md).

## License

Undecided (private for now). Record the decision here when made.
