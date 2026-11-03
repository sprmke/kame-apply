"""Scheduler helper: list workspace ids without tenant context (Phase 10/14).

The minute tick must find every workspace's due schedules. Tenant RLS hides the `workspaces`
table from a context-less transaction, so the scheduler calls this SECURITY DEFINER function
which exposes ids only. Nothing else is readable through it.

Revision ID: 0035
Revises: 0034
Create Date: 2026-11-03
"""

from __future__ import annotations

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.scheduler_workspace_ids()
        RETURNS SETOF uuid
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT id FROM public.workspaces WHERE deleted_at IS NULL
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION public.scheduler_workspace_ids() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.scheduler_workspace_ids() TO kame_apply_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.scheduler_workspace_ids()")
