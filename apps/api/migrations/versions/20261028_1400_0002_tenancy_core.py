"""users, workspaces, workspace_members, RLS foundation

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import USER_EXPR, WORKSPACE_EXPR, tenant_rls_sql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("timezone", sa.String(64), server_default="UTC", nullable=False),
        sa.Column("locale", sa.String(16), server_default="en", nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(16), server_default="personal", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_workspaces"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_workspaces_created_by_users"),
        sa.CheckConstraint("kind IN ('personal', 'team')", name="ck_workspaces_kind"),
    )

    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", "user_id", name="pk_workspace_members"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_workspace_members_workspace_id_workspaces"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_workspace_members_user_id_users"),
        sa.CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="ck_workspace_members_role"),
    )
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    # --- RLS ---
    # workspace_members: a user sees their own memberships (needed to resolve the active workspace
    # before app.workspace_id is set) and every membership of the active workspace.
    op.execute("ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspace_members FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY member_visibility ON workspace_members "
        f"USING (user_id = {USER_EXPR} OR workspace_id = {WORKSPACE_EXPR}) "
        f"WITH CHECK (workspace_id = {WORKSPACE_EXPR})"
    )
    # workspaces: visible to its members. INSERT is allowed for the creating user (sign-up flow).
    op.execute("ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspaces FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY workspace_visibility ON workspaces "
        f"USING (id = {WORKSPACE_EXPR} OR id IN "
        f"(SELECT workspace_id FROM workspace_members WHERE user_id = {USER_EXPR} AND is_active)) "
        f"WITH CHECK (id = {WORKSPACE_EXPR} OR created_by = {USER_EXPR})"
    )
    # activity_log: tenant rows scoped; platform rows (NULL workspace) writable, never readable.
    for stmt in tenant_rls_sql("activity_log", allow_null_workspace_insert=True):
        op.execute(stmt)
    # The app role may append and read the audit trail but never rewrite it (triggers also block).
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON activity_log FROM kame_apply_app")
    # No FK from activity_log to workspaces on purpose: ON DELETE actions would UPDATE audit rows,
    # which the append-only trigger forbids, and the trail must outlive a deleted workspace.


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON activity_log")
    op.execute("ALTER TABLE activity_log NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE activity_log DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS workspace_visibility ON workspaces")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("users")
