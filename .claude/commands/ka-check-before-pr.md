# ka-check-before-pr

1. Run the quality gate: `pnpm run ci:quality` (lint, types, filenames, build, tests, tooling sync, stack terminology, evals-lite). Fix failures first.
2. Spawn the `verifier` agent to walk the phase's exit criteria and acceptance scenarios against the running app.
3. Auth, tenancy, PII, ingestion, MCP, or extension changes: run the `security-auditor` agent.
4. UI changes: run `/ka-design-review` with screenshots at 375/820/1440 (light and dark).
5. Confirm docs were updated in the same change and the phase checklist is ticked.
