---
name: fastapi-stack
description: FastAPI + SQLAlchemy 2 async + Alembic + DBOS + uv conventions for apps/api. Use when adding routers, services, models, or workflows.
---

# FastAPI stack

| Piece | Path / tool |
| --- | --- |
| API entry | `apps/api/app/main.py` |
| Routers | `app/<module>/router.py`, thin: parse, authorize, call a service |
| Services | `app/<module>/service.py`, the only place that writes DB state |
| Models | `app/<module>/models.py` (SQLAlchemy 2 async) |
| Schemas | `app/<module>/schemas.py` (Pydantic v2; source of the OpenAPI spec) |
| Workflows | `app/<module>/workflows.py` (DBOS), see `dbos-workflows` skill |
| Migrations | Alembic `apps/api/migrations/` |
| Config | Pydantic Settings `app/core/config.py` |

Modules are listed in `docs/architecture/overview.md` §2. Workflows, AI tools, MCP tools and the extension all call the same service functions; never duplicate logic.

Run: `uv run` for everything Python (`pnpm run dev:api` wraps it). Local Postgres via `pnpm run dev:docker`. Every request sets `app.workspace_id` for RLS, see `workspace-scoping`.
