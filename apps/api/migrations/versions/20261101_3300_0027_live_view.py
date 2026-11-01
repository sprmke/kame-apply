"""Live view control state on apply_runs (Phase 16).

Revision ID: 0027
Revises: 0026
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "apply_runs",
        sa.Column("control_mode", sa.Text(), server_default="agent", nullable=False),
    )
    op.add_column(
        "apply_runs",
        sa.Column("live_mode", sa.Text(), server_default="off", nullable=False),
    )
    op.add_column(
        "apply_runs",
        sa.Column("controller_user_id", _UUID, sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "apply_runs",
        sa.Column("user_edited_fields", postgresql.JSONB(), server_default="[]", nullable=False),
    )
    op.add_column(
        "apply_runs",
        sa.Column("live_telemetry", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.create_check_constraint(
        "ck_apply_runs_control_mode",
        "apply_runs",
        "control_mode IN ('agent','human','paused')",
    )
    op.create_check_constraint(
        "ck_apply_runs_live_mode",
        "apply_runs",
        "live_mode IN ('off','screencast','screenshot')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_apply_runs_live_mode", "apply_runs", type_="check")
    op.drop_constraint("ck_apply_runs_control_mode", "apply_runs", type_="check")
    for col in (
        "live_telemetry",
        "user_edited_fields",
        "controller_user_id",
        "live_mode",
        "control_mode",
    ):
        op.drop_column("apply_runs", col)
