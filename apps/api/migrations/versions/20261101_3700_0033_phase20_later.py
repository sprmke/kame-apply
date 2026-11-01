"""Phase 20: response tracking, interview prep, gaps, referrals.

Revision ID: 0033
Revises: 0032
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def _table(name: str, *cols: sa.Column) -> None:
    op.create_table(name, *cols)
    for stmt in tenant_rls_sql(name):
        op.execute(stmt)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {name} TO kame_apply_app")


def upgrade() -> None:
    _table(
        "response_messages",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            _UUID,
            sa.ForeignKey("applications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sender", sa.Text(), server_default="", nullable=False),
        sa.Column("subject", sa.Text(), server_default="", nullable=False),
        sa.Column("body_text", sa.Text(), server_default="", nullable=False),
        sa.Column("classification", sa.Text(), server_default="unknown", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("scam_level", sa.Text(), server_default="green", nullable=False),
        sa.Column("scam_reasons", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("r2_raw", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "classification IN ("
            "'rejection','interview','assessment','info_request','offer','unknown')",
            name="ck_response_messages_classification",
        ),
    )
    op.create_index("ix_response_messages_ws", "response_messages", ["workspace_id", "created_at"])

    _table(
        "status_proposals",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            _UUID,
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "response_message_id",
            _UUID,
            sa.ForeignKey("response_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("from_status", sa.Text(), nullable=False),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("citation", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected')",
            name="ck_status_proposals_status",
        ),
    )

    _table(
        "interview_preps",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            _UUID,
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("company_brief", sa.Text(), server_default="", nullable=False),
        sa.Column("likely_questions", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("star_stories", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("checklist", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("citations", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    _table(
        "gap_plan_items",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "track_id", _UUID, sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("skill", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), server_default="", nullable=False),
        sa.Column("resource_url", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.Text(), server_default="open", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('open','in_progress','done','skipped')",
            name="ck_gap_plan_items_status",
        ),
    )

    _table(
        "contacts",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), server_default="", nullable=False),
        sa.Column("company", sa.Text(), server_default="", nullable=False),
        sa.Column("title", sa.Text(), server_default="", nullable=False),
        sa.Column("linkedin_url", sa.Text(), server_default="", nullable=False),
        sa.Column("source", sa.Text(), server_default="csv", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_contacts_ws_company", "contacts", ["workspace_id", "company"])

    _table(
        "referral_drafts",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            _UUID,
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            _UUID,
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("draft", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    for t in (
        "referral_drafts",
        "contacts",
        "gap_plan_items",
        "interview_preps",
        "status_proposals",
        "response_messages",
    ):
        op.drop_table(t)
