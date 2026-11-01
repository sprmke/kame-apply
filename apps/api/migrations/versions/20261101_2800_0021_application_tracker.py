"""Application events, reminders, metrics; expanded status machine.

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_NEW_STATUSES = (
    "draft",
    "ready",
    "in_progress",
    "needs_you",
    "submitted",
    "applied",  # legacy alias of submitted
    "responded",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "ghosted",
    "job_closed",
)


def upgrade() -> None:
    op.execute("UPDATE applications SET status = 'submitted' WHERE status = 'applied'")
    for name in (
        "ck_applications_status",
        "ck_applications_ck_applications_status",
    ):
        op.execute(f"ALTER TABLE applications DROP CONSTRAINT IF EXISTS {name}")
    op.create_check_constraint(
        "status",
        "applications",
        "status IN (" + ",".join(f"'{s}'" for s in _NEW_STATUSES) + ")",
    )

    op.add_column(
        "applications",
        sa.Column("company_name", sa.String(200), server_default="", nullable=False),
    )
    op.add_column(
        "applications",
        sa.Column("job_title", sa.String(300), server_default="", nullable=False),
    )
    op.add_column(
        "applications",
        sa.Column("apply_url", sa.String(500), server_default="", nullable=False),
    )
    op.add_column(
        "applications",
        sa.Column("follow_up_draft", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "applications",
        sa.Column("reminder_days", sa.Integer(), server_default="7", nullable=False),
    )
    op.add_column(
        "applications",
        sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("interview_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("outcome_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("ghosted_suggested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("tailored", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "applications",
        sa.Column("lens_grade", sa.String(8), server_default="", nullable=False),
    )
    op.add_column(
        "applications",
        sa.Column("source_key", sa.String(64), server_default="", nullable=False),
    )
    op.create_index(
        "ix_applications_workspace_submitted",
        "applications",
        ["workspace_id", "submitted_at"],
    )

    op.create_table(
        "application_events",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("application_id", _UUID, nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor_type", sa.String(16), server_default="user", nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_application_events"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_application_events_ws",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
            name="fk_application_events_app",
        ),
    )
    op.create_index(
        "ix_application_events_app_at",
        "application_events",
        ["application_id", "at"],
    )
    for stmt in tenant_rls_sql("application_events"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON application_events FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON application_events TO kame_apply_app")

    op.create_table(
        "application_reminders",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("application_id", _UUID, nullable=False),
        sa.Column("kind", sa.String(32), server_default="follow_up", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("draft", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_application_reminders"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_application_reminders_ws",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
            name="fk_application_reminders_app",
        ),
    )
    op.create_index(
        "ix_application_reminders_due",
        "application_reminders",
        ["workspace_id", "due_at"],
    )
    for stmt in tenant_rls_sql("application_reminders"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON application_reminders FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON application_reminders TO kame_apply_app")

    op.create_table(
        "application_metrics_daily",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("discovered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("matched", sa.Integer(), server_default="0", nullable=False),
        sa.Column("shortlisted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("submitted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("responded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("interview", sa.Integer(), server_default="0", nullable=False),
        sa.Column("offer", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rejected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("withdrawn", sa.Integer(), server_default="0", nullable=False),
        sa.Column("by_method", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("by_tailored", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_application_metrics_daily"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_application_metrics_daily_ws",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
            name="fk_application_metrics_daily_track",
        ),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_application_metrics_overall "
        "ON application_metrics_daily (workspace_id, day) WHERE track_id IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_application_metrics_track "
        "ON application_metrics_daily (workspace_id, track_id, day) "
        "WHERE track_id IS NOT NULL"
    )
    for stmt in tenant_rls_sql("application_metrics_daily"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON application_metrics_daily FROM kame_apply_ro")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON application_metrics_daily TO kame_apply_app"
    )

    op.create_table(
        "application_saved_views",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("filters", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_application_saved_views"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_application_saved_views_ws",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_application_saved_views_user"
        ),
    )
    for stmt in tenant_rls_sql("application_saved_views"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON application_saved_views FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON application_saved_views TO kame_apply_app")


def downgrade() -> None:
    op.drop_table("application_saved_views")
    op.drop_table("application_metrics_daily")
    op.drop_table("application_reminders")
    op.drop_table("application_events")
    op.drop_index("ix_applications_workspace_submitted", table_name="applications")
    for col in (
        "source_key",
        "lens_grade",
        "tailored",
        "ghosted_suggested_at",
        "outcome_at",
        "interview_at",
        "responded_at",
        "reminder_at",
        "reminder_days",
        "follow_up_draft",
        "apply_url",
        "job_title",
        "company_name",
    ):
        op.drop_column("applications", col)
    op.execute(
        "UPDATE applications SET status = 'applied' WHERE status IN "
        "('submitted','in_progress','needs_you','ghosted')"
    )
    for name in (
        "ck_applications_status",
        "ck_applications_ck_applications_status",
    ):
        op.execute(f"ALTER TABLE applications DROP CONSTRAINT IF EXISTS {name}")
    op.create_check_constraint(
        "status",
        "applications",
        "status IN ("
        "'draft','ready','applied','responded','interview','offer',"
        "'rejected','withdrawn','job_closed')",
    )
