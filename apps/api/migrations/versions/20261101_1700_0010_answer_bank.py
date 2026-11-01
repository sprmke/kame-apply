"""answer_bank: reusable form answers per profile

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "answer_bank"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("profile_id", _UUID, nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        # Optional ISO 3166-1 alpha-2 for country-scoped keys (e.g. work_authorization).
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column(
            "question_variants",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("answer", sa.Text(), server_default="", nullable=False),
        # Optional structured payload (salary currency/period, work-auth details). Text stays canonical.
        sa.Column("answer_json", postgresql.JSONB(), nullable=True),
        sa.Column("scope", sa.String(12), server_default="global", nullable=False),
        # Track FK lands in Phase 4; store the id now so track-scoped rows can exist early.
        sa.Column("track_id", _UUID, nullable=True),
        sa.Column("approved", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", _UUID, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_answer_bank"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_answer_bank_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_answer_bank_profile_id_candidate_profiles",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_answer_bank_created_by_users"
        ),
        sa.CheckConstraint("scope IN ('global','track')", name="ck_answer_bank_scope"),
        sa.CheckConstraint(
            "(scope = 'global' AND track_id IS NULL) OR (scope = 'track' AND track_id IS NOT NULL)",
            name="ck_answer_bank_scope_track",
        ),
        sa.CheckConstraint(
            "country IS NULL OR country ~ '^[A-Z]{2}$'",
            name="ck_answer_bank_country",
        ),
        sa.CheckConstraint("char_length(key) >= 2", name="ck_answer_bank_key_len"),
    )
    op.create_index("ix_answer_bank_workspace_profile", _TABLE, ["workspace_id", "profile_id"])
    # One row per (profile, key, country, scope, track). coalesce so NULLs collide.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_answer_bank_slot
        ON answer_bank (
            profile_id,
            key,
            scope,
            COALESCE(country, ''),
            COALESCE(track_id, '00000000-0000-0000-0000-000000000000'::uuid)
        )
        """
    )
    for stmt in tenant_rls_sql(_TABLE):
        op.execute(stmt)
    op.execute(f"REVOKE ALL ON {_TABLE} FROM kame_apply_ro")


def downgrade() -> None:
    op.drop_table(_TABLE)
