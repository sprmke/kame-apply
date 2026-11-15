"""Setup drafts: one row per resume reading that fills the pages about a person.

Revision ID: 0042
Revises: 0039
Create Date: 2026-11-13

Numbering note: 0040 and 0041 belong to the multi-industry work. If that lands first, re-point
`down_revision` at 0041 in the same change that resolves the merge.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0042"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "setup_drafts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subject", sa.String(16), nullable=False, server_default="self"),
        sa.Column("mode", sa.String(16), nullable=False, server_default="new"),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("role_text", sa.Text(), nullable=True),
        sa.Column(
            "inputs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "steps",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("bundle", postgresql.JSONB(), nullable=True),
        sa.Column(
            "decisions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "base",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("apply_key", sa.String(64), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("ai_cost_micros", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('queued','running','ready','applying','applied','failed','cancelled',"
            "'discarded','expired','reverted')",
            name="ck_setup_drafts_status",
        ),
        sa.CheckConstraint("subject IN ('self','other_person')", name="ck_setup_drafts_subject"),
        sa.CheckConstraint("mode IN ('new','update')", name="ck_setup_drafts_mode"),
        sa.CheckConstraint("ai_cost_micros >= 0", name="ck_setup_drafts_cost"),
    )
    op.create_index(
        "uq_setup_drafts_open_profile",
        "setup_drafts",
        ["profile_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued','running','ready','applying')"),
    )
    op.create_index(
        "ix_setup_drafts_workspace_created",
        "setup_drafts",
        ["workspace_id", sa.text("created_at DESC")],
    )
    for stmt in tenant_rls_sql("setup_drafts"):
        op.execute(stmt)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON setup_drafts TO kame_apply_app")


def downgrade() -> None:
    op.drop_table("setup_drafts")
