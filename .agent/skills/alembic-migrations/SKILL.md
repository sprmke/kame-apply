---
name: alembic-migrations
description: Alembic migration habits for Kame Apply: new file only, RLS on tenant tables, indexes, extensions.
---

# Alembic migrations

- Never edit a shipped migration under `apps/api/migrations/versions/`; add a new one (a hook blocks edits).
- Autogenerate, then **review by hand**: missing indexes on `workspace_id` and FKs, enum changes, server defaults.
- Every tenant table: `workspace_id NOT NULL`, `ENABLE`/`FORCE ROW LEVEL SECURITY`, policy keyed on `current_setting('app.workspace_id')`. Use the template helper from Phase 2.
- Extensions (`vector`, `pg_trgm`, `pgcrypto`) are enabled in an explicit migration.
- Migrations run with the migration role; the app role has no `BYPASSRLS`.
- Local only by default (`pnpm run db:migrate`). Prod migrations need the unlock word (`no-prod-deploy.mdc`).
- Data backfills are separate, idempotent, and documented in `docs/architecture/deployment.md`.
