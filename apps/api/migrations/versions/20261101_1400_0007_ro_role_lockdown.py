"""revoke tenant tables from the read-only role

The read-only role (postgres MCP, dev only) can SET app.workspace_id itself, so RLS would not hold
it back. It must not read tenant tables at all.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-01
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

TABLES = ("activity_log", "workspaces", "workspace_members")


def upgrade() -> None:
    for t in TABLES:
        op.execute(f"REVOKE ALL ON {t} FROM kame_apply_ro")


def downgrade() -> None:
    for t in TABLES:
        op.execute(f"GRANT SELECT ON {t} TO kame_apply_ro")
