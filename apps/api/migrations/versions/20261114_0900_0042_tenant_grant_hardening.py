"""Revoke read-only role access from new tenant tables.

Revision ID: 0042
Revises: 0041
Create Date: 2026-11-14

`workspace_industries` and `profile_facets` are tenant-owned and RLS-scoped. The read-only
role must not see them, matching every other tenant table.
"""

from __future__ import annotations

from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

_TABLES = ("workspace_industries", "profile_facets")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"REVOKE ALL ON {table} FROM kame_apply_ro")
    op.execute(
        "UPDATE sources SET last_error = regexp_replace("
        "last_error, '(app_key|app_id|api_key|key)=[^&[:space:]]+', '\\1=***', 'gi'"
        ") WHERE last_error IS NOT NULL"
    )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"GRANT SELECT ON {table} TO kame_apply_ro")
