"""Widen profile_certifications.kind so 'certification' fits.

The original column is varchar(12) while the check constraint and the Pydantic literal both use
'certification' (13 characters), so every insert of a certification failed with
"value too long for type character varying(12)".

Revision ID: 0039
Revises: 0038
Create Date: 2026-11-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "profile_certifications",
        "kind",
        existing_type=sa.String(12),
        type_=sa.String(16),
        existing_nullable=False,
        existing_server_default="certification",
    )


def downgrade() -> None:
    op.execute("UPDATE profile_certifications SET kind = 'license' WHERE kind = 'certification'")
    op.alter_column(
        "profile_certifications",
        "kind",
        existing_type=sa.String(16),
        type_=sa.String(12),
        existing_nullable=False,
        existing_server_default="certification",
    )
