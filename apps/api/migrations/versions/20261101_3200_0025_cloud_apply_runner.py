"""Cloud apply runner: checkpoints, runner tokens, site sessions, run columns (Phase 15).

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("apply_runs", sa.Column("runner_id", sa.Text(), nullable=True))
    op.add_column("apply_runs", sa.Column("dbos_workflow_id", sa.Text(), nullable=True))
    op.add_column(
        "apply_runs",
        sa.Column("policy", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.add_column(
        "apply_runs",
        sa.Column("submit_approved", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("apply_runs", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column(
        "apply_runs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("apply_runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("apply_runs", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "apply_runs",
        sa.Column("ats", sa.Text(), server_default="generic", nullable=False),
    )
    op.add_column(
        "apply_runs",
        sa.Column("last_step_seq", sa.Integer(), server_default="0", nullable=False),
    )

    op.add_column("apply_run_steps", sa.Column("screenshot_r2", sa.Text(), nullable=True))
    op.add_column(
        "apply_run_steps",
        sa.Column("outcome", sa.Text(), server_default="ok", nullable=False),
    )

    op.create_table(
        "apply_checkpoints",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id", _UUID, sa.ForeignKey("apply_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("detail", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.Text(), server_default="open", nullable=False),
        sa.Column("decided_by", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decision", postgresql.JSONB(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('login','captcha','ai_restricted','sensitive_field','unknown_required',"
            "'answer_approval','risk','final_review','blocked')",
            name="ck_apply_checkpoints_kind",
        ),
        sa.CheckConstraint(
            "status IN ('open','resolved','expired')",
            name="ck_apply_checkpoints_status",
        ),
    )
    op.create_index("ix_apply_checkpoints_run", "apply_checkpoints", ["run_id", "status"])
    for stmt in tenant_rls_sql("apply_checkpoints"):
        op.execute(stmt)

    op.create_table(
        "runner_tokens",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("label", sa.Text(), server_default="cloud", nullable=False),
        sa.Column("mode", sa.Text(), server_default="cloud", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("mode IN ('cloud','local')", name="ck_runner_tokens_mode"),
    )
    op.create_index("ix_runner_tokens_ws", "runner_tokens", ["workspace_id"])
    for stmt in tenant_rls_sql("runner_tokens"):
        op.execute(stmt)

    op.create_table(
        "site_sessions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("site", sa.Text(), nullable=False),
        sa.Column("encrypted_storage_state", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workspace_id", "site", name="uq_site_sessions_ws_site"),
    )
    for stmt in tenant_rls_sql("site_sessions"):
        op.execute(stmt)

    for table in ("apply_checkpoints", "runner_tokens", "site_sessions"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO kame_apply_app")


def downgrade() -> None:
    op.drop_table("site_sessions")
    op.drop_table("runner_tokens")
    op.drop_table("apply_checkpoints")
    op.drop_column("apply_run_steps", "outcome")
    op.drop_column("apply_run_steps", "screenshot_r2")
    for col in (
        "last_step_seq",
        "ats",
        "ended_at",
        "started_at",
        "heartbeat_at",
        "failure_reason",
        "submit_approved",
        "policy",
        "dbos_workflow_id",
        "runner_id",
    ):
        op.drop_column("apply_runs", col)
