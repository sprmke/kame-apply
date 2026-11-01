"""profile_proposals: interview drafts the user accepts or rejects

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "profile_proposals"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("profile_id", _UUID, nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("target_type", sa.String(24), nullable=False),
        sa.Column("target_id", _UUID, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        # User reply used to build the proposal. Never written to activity_log.
        sa.Column("user_answer", sa.Text(), server_default="", nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("created_by", _UUID, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_profile_proposals"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_profile_proposals_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_profile_proposals_profile_id_candidate_profiles",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_profile_proposals_created_by_users"
        ),
        sa.CheckConstraint(
            "kind IN ('bullet_metric','bullet_text','skill_years','gap_note')",
            name="ck_profile_proposals_kind",
        ),
        sa.CheckConstraint(
            "target_type IN ('bullet','skill','experience')",
            name="ck_profile_proposals_target_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected')",
            name="ck_profile_proposals_status",
        ),
    )
    op.create_index(
        "ix_profile_proposals_workspace_profile_status",
        _TABLE,
        ["workspace_id", "profile_id", "status"],
    )
    for stmt in tenant_rls_sql(_TABLE):
        op.execute(stmt)
    op.execute(f"REVOKE ALL ON {_TABLE} FROM kame_apply_ro")


def downgrade() -> None:
    op.drop_table(_TABLE)
