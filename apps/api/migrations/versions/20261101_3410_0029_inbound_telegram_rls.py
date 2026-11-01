"""Allow inbound token and Telegram link-code lookups before workspace context.

Revision ID: 0029
Revises: 0028
Create Date: 2026-11-01
"""

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON telegram_links")
    op.execute(
        "CREATE POLICY tenant_isolation ON telegram_links "
        "USING ("
        "workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid "
        "OR ("
        "NULLIF(current_setting('app.workspace_id', true), '') IS NULL "
        "AND link_code IS NOT NULL"
        ")"
        ") WITH CHECK ("
        "workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid"
        ")"
    )

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON inbound_addresses")
    op.execute(
        "CREATE POLICY tenant_isolation ON inbound_addresses "
        "USING ("
        "workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid "
        "OR NULLIF(current_setting('app.workspace_id', true), '') IS NULL"
        ") WITH CHECK ("
        "workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid"
        ")"
    )


def downgrade() -> None:
    from app.core.rls import tenant_rls_sql

    for table in ("telegram_links", "inbound_addresses"):
        for stmt in tenant_rls_sql(table):
            op.execute(stmt)
