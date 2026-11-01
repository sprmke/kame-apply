---
name: fix-migration-issues
description: Fix local schema drift or missing columns after pulling or adding an Alembic migration. Local Postgres only.
---

# Fix migration issues (local)

1. Local Postgres up: `pnpm run dev:docker`; check `pnpm run env:status` shows a local URL.
2. `pnpm run db:migrate` (`alembic upgrade head`).
3. Multiple heads: `uv run alembic heads`, then add a merge revision. Never edit shipped revisions.
4. Autogenerate shows unexpected diffs: the DB is stale or a model import is missing from `migrations/env.py`.
5. Last resort, destructive: `pnpm run db:reset:local` (drops local data, re-migrates, re-seeds). Ask first.

Never run these against a hosted URL without the unlock word (`no-prod-deploy.mdc`).
