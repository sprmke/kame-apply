"""Schedules, notifications, prefs; tracks may pause.

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.drop_constraint("ck_tracks_status", "tracks", type_="check")
    op.create_check_constraint(
        "ck_tracks_status",
        "tracks",
        "status IN ('active','paused','archived')",
    )

    op.create_table(
        "schedules",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=False),
        sa.Column("scope", sa.String(16), server_default="all", nullable=False),
        sa.Column("source_id", _UUID, nullable=True),
        sa.Column("preset", sa.String(32), server_default="custom", nullable=False),
        sa.Column("cron", sa.String(64), nullable=False),
        sa.Column("timezone", sa.String(64), server_default="UTC", nullable=False),
        sa.Column("quiet_hours", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("daily_cap", sa.Integer(), server_default="12", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_skip_reason", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_schedules"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_schedules_ws"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_schedules_track"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], ondelete="SET NULL", name="fk_schedules_source"
        ),
        sa.CheckConstraint("scope IN ('all','source')", name="ck_schedules_scope"),
        sa.CheckConstraint("daily_cap >= 0 AND daily_cap <= 48", name="ck_schedules_daily_cap"),
    )
    op.create_index("ix_schedules_due", "schedules", ["enabled", "next_run_at"])
    op.create_index("ix_schedules_track", "schedules", ["workspace_id", "track_id"])
    for stmt in tenant_rls_sql("schedules"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON schedules FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON schedules TO kame_apply_app")

    op.create_table(
        "notifications",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), server_default="", nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("dedupe_key", sa.String(200), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_notifications_ws"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_notifications_user"
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            "type",
            "dedupe_key",
            name="uq_notifications_dedupe",
        ),
    )
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["workspace_id", "user_id", "created_at"],
    )
    for stmt in tenant_rls_sql("notifications"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON notifications FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON notifications TO kame_apply_app")

    op.create_table(
        "notification_prefs",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notification_prefs"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_notification_prefs_ws",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_notification_prefs_user"
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            "channel",
            "event",
            name="uq_notification_prefs",
        ),
        sa.CheckConstraint("channel IN ('in_app','email')", name="ck_notification_prefs_channel"),
    )
    op.create_index(
        "ix_notification_prefs_user",
        "notification_prefs",
        ["workspace_id", "user_id"],
    )
    for stmt in tenant_rls_sql("notification_prefs"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON notification_prefs FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON notification_prefs TO kame_apply_app")

    op.create_table(
        "email_unsubscribes",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_unsubscribes"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_email_unsubscribes_ws",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_email_unsubscribes_user"
        ),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_email_unsubscribes"),
    )
    for stmt in tenant_rls_sql("email_unsubscribes"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON email_unsubscribes FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON email_unsubscribes TO kame_apply_app")


def downgrade() -> None:
    op.drop_table("email_unsubscribes")
    op.drop_table("notification_prefs")
    op.drop_table("notifications")
    op.drop_table("schedules")
    op.drop_constraint("ck_tracks_status", "tracks", type_="check")
    op.create_check_constraint(
        "ck_tracks_status",
        "tracks",
        "status IN ('active','archived')",
    )
