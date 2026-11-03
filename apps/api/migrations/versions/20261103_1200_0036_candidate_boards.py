"""Allow candidate company boards (generated slugs that are not yet validated).

Revision ID: 0036
Revises: 0035
Create Date: 2026-11-03
"""

from __future__ import annotations

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_company_boards_status", "company_boards", type_="check")
    op.create_check_constraint(
        "ck_company_boards_status",
        "company_boards",
        "status IN ('active','inactive','pending','candidate')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM company_boards WHERE status = 'candidate'")
    op.drop_constraint("ck_company_boards_status", "company_boards", type_="check")
    op.create_check_constraint(
        "ck_company_boards_status",
        "company_boards",
        "status IN ('active','inactive','pending')",
    )
