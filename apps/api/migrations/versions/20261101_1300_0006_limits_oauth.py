"""workspace_limits, oauth_identities

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # Per-workspace caps. Defaults apply when no row exists; a row overrides (plan changes, support).
    op.create_table(
        "workspace_limits",
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("max_members", sa.Integer(), server_default="10", nullable=False),
        sa.Column("max_ai_credentials", sa.Integer(), server_default="10", nullable=False),
        sa.Column("max_tracks", sa.Integer(), server_default="5", nullable=False),
        sa.Column("max_sources", sa.Integer(), server_default="25", nullable=False),
        sa.Column("max_storage_mb", sa.Integer(), server_default="500", nullable=False),
        sa.Column("max_ai_budget_cents", sa.Integer(), server_default="10000", nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", name="pk_workspace_limits"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_workspace_limits_workspace_id_workspaces"),
    )
    for stmt in tenant_rls_sql("workspace_limits"):
        op.execute(stmt)
    # Tenants read their limits but only the platform (owner role) changes them.
    op.execute("REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON workspace_limits FROM kame_apply_app")
    op.execute("REVOKE ALL ON workspace_limits FROM kame_apply_ro")

    # Global like users: a Google identity maps to exactly one account.
    op.create_table(
        "oauth_identities",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_oauth_identities"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_oauth_identities_user_id_users"),
        sa.UniqueConstraint("provider", "subject", name="uq_oauth_identities_provider"),
        sa.UniqueConstraint("user_id", "provider", name="uq_oauth_identities_user_id"),
    )
    op.execute("REVOKE ALL ON oauth_identities FROM kame_apply_ro")


def downgrade() -> None:
    op.drop_table("oauth_identities")
    op.drop_table("workspace_limits")
