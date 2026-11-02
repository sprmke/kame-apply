"""Allow push and Telegram notification preferences (Phase 17).

Revision ID: 0034
Revises: 0033
Create Date: 2026-11-03
"""

from __future__ import annotations

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_notification_prefs_channel", "notification_prefs", type_="check")
    op.create_check_constraint(
        "ck_notification_prefs_channel",
        "notification_prefs",
        "channel IN ('in_app','email','push','telegram')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM notification_prefs WHERE channel IN ('push','telegram')")
    op.drop_constraint("ck_notification_prefs_channel", "notification_prefs", type_="check")
    op.create_check_constraint(
        "ck_notification_prefs_channel",
        "notification_prefs",
        "channel IN ('in_app','email')",
    )
