"""Workspace purge helper: find soft-deleted workspaces past the recovery window.

Revision ID: 0037
Revises: 0036
Create Date: 2026-11-04
"""

from __future__ import annotations

from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workspaces_deleted_at ON workspaces (deleted_at) "
        "WHERE deleted_at IS NOT NULL"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.deleted_workspace_ids_before(cutoff timestamptz)
        RETURNS SETOF uuid
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT id FROM public.workspaces
            WHERE deleted_at IS NOT NULL AND deleted_at < cutoff
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION public.deleted_workspace_ids_before(timestamptz) FROM PUBLIC")
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.deleted_workspace_ids_before(timestamptz) "
        "TO kame_apply_app"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.deleted_workspace_ids_before(timestamptz)")
    op.execute("DROP INDEX IF EXISTS ix_workspaces_deleted_at")
