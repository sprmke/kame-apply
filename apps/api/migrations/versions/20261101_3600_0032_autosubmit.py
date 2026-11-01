"""Auto-submit dry-run reports (Phase 19).

Revision ID: 0032
Revises: 0031
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "autosubmit_dry_runs",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "track_id", _UUID, sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "application_id",
            _UUID,
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", _UUID, nullable=True),
        sa.Column("would_submit", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("reasons", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_autosubmit_dry_runs_track", "autosubmit_dry_runs", ["workspace_id", "track_id"]
    )
    for stmt in tenant_rls_sql("autosubmit_dry_runs"):
        op.execute(stmt)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON autosubmit_dry_runs TO kame_apply_app")


def downgrade() -> None:
    op.drop_table("autosubmit_dry_runs")
