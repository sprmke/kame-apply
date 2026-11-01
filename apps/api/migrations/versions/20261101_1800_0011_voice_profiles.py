"""voice_profiles: writing samples, style JSON, banned phrases

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "voice_profiles"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("profile_id", _UUID, nullable=False),
        # Pasted writing samples. Not logged; kept for re-analysis.
        sa.Column("samples", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("style", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "banned_phrases",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", _UUID, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_voice_profiles"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_voice_profiles_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_voice_profiles_profile_id_candidate_profiles",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_voice_profiles_created_by_users"
        ),
        sa.UniqueConstraint("profile_id", name="uq_voice_profiles_profile_id"),
    )
    op.create_index("ix_voice_profiles_workspace_id", _TABLE, ["workspace_id"])
    for stmt in tenant_rls_sql(_TABLE):
        op.execute(stmt)
    op.execute(f"REVOKE ALL ON {_TABLE} FROM kame_apply_ro")


def downgrade() -> None:
    op.drop_table(_TABLE)
