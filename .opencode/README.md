# OpenCode — Kame Apply

- Config: root `opencode.json`
- Commands: symlinked from `.claude/commands/`
- Hooks: `.opencode/plugins/ka-ai-tooling.ts`
- Agents: `.opencode/agents/` (`debugger`, `security-auditor`, `test-runner`, `verifier`, `design-reviewer`)

Same goals as Cursor/Claude; see `.cursor/rules/README.md`. The plugin reuses the shell, migration, formatter, stack, and docs hooks from `.claude/hooks/`. Agents and commands are symlinks created by `pnpm run setup:ai-tooling`.
