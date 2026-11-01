---
name: docs-first
description: Read the phase file and linked docs before implementing anything. Use at the start of every module task.
---

# Docs first

1. `docs/phases/README.md`: confirm the current phase and its dependencies are done.
2. The phase file: goal, tasks, data model, API, edge cases, exit criteria.
3. Linked docs only: `docs/prd.md` (scope, principles P1–P7), `docs/tech-stack.md`, `docs/architecture/overview.md`, the relevant `docs/research/*`, and `docs/design/*` for UI.
4. The glob-scoped rule for the surface you are touching (`.cursor/rules/README.md`).
5. If the docs and the request conflict, stop and ask; if scope changes, edit the phase file and `prd.md` in the same change.

Library APIs change: use `context7` for FastAPI, SQLAlchemy, DBOS, PydanticAI, Nuxt, WXT before relying on memory.
