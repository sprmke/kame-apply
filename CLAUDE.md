# CLAUDE.md

Claude Code adapter. **Canonical guidance lives in `AGENTS.md`.**

@AGENTS.md

## Claude Code only

- `.cursor/rules/*.mdc` are not auto-loaded here. The always-on ones are listed in `opencode.json`; read the matching rule when a task touches that surface.
- SessionStart and PostToolUse hooks inject the docs-sync reminder.
- Before claiming a material change done, invoke `documentation-maintenance`, `route-guides`, `audit-logging`, and `workspace-scoping` when the change touches those surfaces.
- Subagents: `debugger`, `security-auditor`, `test-runner`, `verifier`, `design-reviewer`. Use them only when the task matches their purpose.
- Tooling index: `.claude/README.md`. Commands start at `/ka-help`.
