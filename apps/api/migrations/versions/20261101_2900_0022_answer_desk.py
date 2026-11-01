"""Answer Desk sessions/items; AI-use stance on voice profiles.

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "voice_profiles",
        sa.Column("ai_use_stance", sa.Text(), server_default="", nullable=False),
    )

    op.create_table(
        "answer_desk_sessions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            _UUID,
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            _UUID,
            sa.ForeignKey("applications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_text", sa.Text(), server_default="", nullable=False),
        sa.Column("page_restricted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_answer_desk_sessions_ws_profile",
        "answer_desk_sessions",
        ["workspace_id", "profile_id"],
    )
    for stmt in tenant_rls_sql("answer_desk_sessions"):
        op.execute(stmt)

    op.create_table(
        "answer_desk_items",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            _UUID,
            sa.ForeignKey("answer_desk_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("constraints", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("ai_restricted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("legal_flag", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("source", sa.String(24), server_default="draft", nullable=False),
        sa.Column("draft", sa.Text(), server_default="", nullable=False),
        sa.Column("fact_notes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("banned_hits", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("char_limit", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(32), server_default="text", nullable=False),
        sa.Column(
            "answer_bank_id",
            _UUID,
            sa.ForeignKey("answer_bank.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "source IN ('draft','bank','restricted','ai_stance','manual','needs_story')",
            name="ck_answer_desk_items_source",
        ),
    )
    op.create_index(
        "ix_answer_desk_items_session",
        "answer_desk_items",
        ["session_id", "sort_order"],
    )
    for stmt in tenant_rls_sql("answer_desk_items"):
        op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS answer_desk_items CASCADE")
    op.execute("DROP TABLE IF EXISTS answer_desk_sessions CASCADE")
    op.drop_column("voice_profiles", "ai_use_stance")
