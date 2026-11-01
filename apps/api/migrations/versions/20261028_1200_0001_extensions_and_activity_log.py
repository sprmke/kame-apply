"""extensions and append-only activity_log

Revision ID: 0001
Revises:
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "activity_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=True),
        sa.Column("action", sa.String(96), nullable=False),
        sa.Column("target_type", sa.String(48), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_activity_log"),
        sa.CheckConstraint("actor_type IN ('user', 'agent', 'system')", name="ck_activity_log_actor_type"),
    )
    op.create_index("ix_activity_log_workspace_created", "activity_log", ["workspace_id", "created_at"])
    op.create_index("ix_activity_log_target", "activity_log", ["target_type", "target_id"])

    # Append-only: no UPDATE or DELETE, not even for the table owner (invariant 5).
    op.execute(
        """
        CREATE FUNCTION activity_log_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'activity_log is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER activity_log_no_update_delete
        BEFORE UPDATE OR DELETE ON activity_log
        FOR EACH ROW EXECUTE FUNCTION activity_log_append_only()
        """
    )
    op.execute(
        """
        CREATE TRIGGER activity_log_no_truncate
        BEFORE TRUNCATE ON activity_log
        FOR EACH STATEMENT EXECUTE FUNCTION activity_log_append_only()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS activity_log_no_truncate ON activity_log")
    op.execute("DROP TRIGGER IF EXISTS activity_log_no_update_delete ON activity_log")
    op.drop_table("activity_log")
    op.execute("DROP FUNCTION IF EXISTS activity_log_append_only()")
    # Extensions are left in place: other objects may depend on them.
