"""Store notify_user_id on inbound_addresses for webhook actor.

Revision ID: 0030
Revises: 0029
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "inbound_addresses",
        sa.Column("notify_user_id", _UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    # Backfill from workspace owners where possible (migration role bypasses RLS).
    op.execute(
        """
        UPDATE inbound_addresses a
        SET notify_user_id = m.user_id
        FROM workspace_members m
        WHERE m.workspace_id = a.workspace_id
          AND m.role = 'owner'
          AND m.is_active
          AND a.notify_user_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("inbound_addresses", "notify_user_id")
