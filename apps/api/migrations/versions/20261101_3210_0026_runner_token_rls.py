"""Allow runner_tokens hash lookup before workspace context (Phase 15).

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-01
"""

from alembic import op

from app.core.rls import WORKSPACE_EXPR

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON runner_tokens")
    op.execute(
        "CREATE POLICY tenant_isolation ON runner_tokens "
        f"USING ("
        f"workspace_id = {WORKSPACE_EXPR} "
        f"OR (NULLIF(current_setting('app.workspace_id', true), '') IS NULL "
        f"AND NULLIF(current_setting('app.user_id', true), '') IS NULL)"
        f") "
        f"WITH CHECK (workspace_id = {WORKSPACE_EXPR} "
        f"OR (NULLIF(current_setting('app.workspace_id', true), '') IS NULL "
        f"AND NULLIF(current_setting('app.user_id', true), '') IS NULL))"
    )


def downgrade() -> None:
    # Restore strict tenant-only policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON runner_tokens")
    op.execute(
        "CREATE POLICY tenant_isolation ON runner_tokens "
        f"USING (workspace_id = {WORKSPACE_EXPR}) "
        f"WITH CHECK (workspace_id = {WORKSPACE_EXPR})"
    )
