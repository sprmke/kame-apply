"""Allow queued tailor runs for background execution.

Revision ID: 0038
Revises: 0037
Create Date: 2026-11-04
"""

from __future__ import annotations

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_tailor_runs_status", "tailor_runs", type_="check")
    op.create_check_constraint(
        "ck_tailor_runs_status",
        "tailor_runs",
        "status IN ('queued','running','ready','accepted','discarded','failed')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM tailor_runs WHERE status = 'queued'")
    op.drop_constraint("ck_tailor_runs_status", "tailor_runs", type_="check")
    op.create_check_constraint(
        "ck_tailor_runs_status",
        "tailor_runs",
        "status IN ('running','ready','accepted','discarded','failed')",
    )
