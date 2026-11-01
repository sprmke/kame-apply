"""invitations

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import WORKSPACE_EXPR

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_INVITE_TOKEN_EXPR = "NULLIF(current_setting('app.invite_token_hash', true), '')"


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("invited_by", _UUID, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_invitations"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_invitations_workspace_id_workspaces"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], name="fk_invitations_invited_by_users"),
        sa.UniqueConstraint("token_hash", name="uq_invitations_token_hash"),
        sa.CheckConstraint("role IN ('admin', 'member', 'viewer')", name="ck_invitations_role"),
    )
    op.create_index("ix_invitations_workspace_id", "invitations", ["workspace_id"])

    op.execute("ALTER TABLE invitations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invitations FORCE ROW LEVEL SECURITY")
    # Tenant access by active workspace. The accept flow has no workspace yet, so it may also see
    # exactly the one row whose token hash it holds (set per transaction by the accept service).
    op.execute(
        f"CREATE POLICY invitation_access ON invitations "
        f"USING (workspace_id = {WORKSPACE_EXPR} OR token_hash = {_INVITE_TOKEN_EXPR}) "
        f"WITH CHECK (workspace_id = {WORKSPACE_EXPR})"
    )
    op.execute("REVOKE ALL ON invitations FROM kame_apply_ro")


def downgrade() -> None:
    op.drop_table("invitations")
