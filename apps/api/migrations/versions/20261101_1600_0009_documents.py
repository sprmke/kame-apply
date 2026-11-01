"""documents: uploaded resumes and related blobs

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLE = "documents"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("profile_id", _UUID, nullable=False),
        sa.Column("kind", sa.String(24), server_default="resume_upload", nullable=False),
        sa.Column("r2_key", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(260), nullable=False),
        sa.Column("mime", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("ocr_used", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), server_default="[]", nullable=False),
        # Cleaned plain text for the parse step. Blobs stay in R2; this is short enough for resumes.
        sa.Column("extracted_text", sa.Text(), nullable=True),
        # LLM draft (ProfileExtract) lands in slice 3; null until then.
        sa.Column("parsed", postgresql.JSONB(), nullable=True),
        sa.Column("parse_quality", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", _UUID, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_documents_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_documents_profile_id_candidate_profiles",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_documents_created_by_users"),
        sa.CheckConstraint(
            "kind IN ('resume_upload','portfolio','generated','paste')",
            name="ck_documents_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending','ready','failed')",
            name="ck_documents_status",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_documents_size_bytes"),
        sa.UniqueConstraint("r2_key", name="uq_documents_r2_key"),
    )
    op.create_index("ix_documents_workspace_profile", _TABLE, ["workspace_id", "profile_id"])
    for stmt in tenant_rls_sql(_TABLE):
        op.execute(stmt)
    op.execute(f"REVOKE ALL ON {_TABLE} FROM kame_apply_ro")


def downgrade() -> None:
    op.drop_table(_TABLE)
