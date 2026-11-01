"""Resume Studio: resume_versions, resume_changes, market_insights.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "resume_versions",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("profile_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=True),
        sa.Column("application_id", _UUID, nullable=True),
        sa.Column("kind", sa.String(16), server_default="base", nullable=False),
        sa.Column("label", sa.String(200), server_default="", nullable=False),
        sa.Column("content", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("template", sa.String(64), server_default="classic", nullable=False),
        sa.Column("page_size", sa.String(16), server_default="letter", nullable=False),
        sa.Column("r2_pdf", sa.String(500), nullable=True),
        sa.Column("r2_docx", sa.String(500), nullable=True),
        sa.Column("r2_txt", sa.String(500), nullable=True),
        sa.Column("critique", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("lens_report", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("parse_gate", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("parent_id", _UUID, nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resume_versions"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_resume_versions_ws"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["candidate_profiles.id"], ondelete="CASCADE", name="fk_resume_versions_profile"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="SET NULL", name="fk_resume_versions_track"
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
            name="fk_resume_versions_parent",
        ),
        sa.CheckConstraint("kind IN ('base','tailored','draft')", name="ck_resume_versions_kind"),
        sa.CheckConstraint(
            "page_size IN ('letter','a4')",
            name="ck_resume_versions_page_size",
        ),
    )
    op.create_index(
        "ix_resume_versions_workspace_track",
        "resume_versions",
        ["workspace_id", "track_id"],
    )
    for stmt in tenant_rls_sql("resume_versions"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON resume_versions FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON resume_versions TO kame_apply_app")

    op.create_table(
        "resume_changes",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("resume_version_id", _UUID, nullable=False),
        sa.Column("path", sa.String(300), nullable=False),
        sa.Column("op", sa.String(32), server_default="rewrite", nullable=False),
        sa.Column("before", sa.Text(), server_default="", nullable=False),
        sa.Column("after", sa.Text(), server_default="", nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "evidence_refs",
            postgresql.ARRAY(_UUID),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("status", sa.String(16), server_default="proposed", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resume_changes"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_resume_changes_ws"
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="CASCADE",
            name="fk_resume_changes_version",
        ),
        sa.CheckConstraint(
            "status IN ('proposed','accepted','rejected')",
            name="ck_resume_changes_status",
        ),
    )
    op.create_index(
        "ix_resume_changes_version_status",
        "resume_changes",
        ["resume_version_id", "status"],
    )
    for stmt in tenant_rls_sql("resume_changes"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON resume_changes FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON resume_changes TO kame_apply_app")

    op.create_table(
        "market_insights",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=False),
        sa.Column("window_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("sample_size", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skills", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("titles", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("salary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("years_required", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("certifications", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("comparison", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("secondary_research", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("low_confidence", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_market_insights"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_market_insights_ws"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_market_insights_track"
        ),
        sa.UniqueConstraint("track_id", "window_days", name="uq_market_insights_track_window"),
    )
    for stmt in tenant_rls_sql("market_insights"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON market_insights FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON market_insights TO kame_apply_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS market_insights CASCADE")
    op.execute("DROP TABLE IF EXISTS resume_changes CASCADE")
    op.execute("DROP TABLE IF EXISTS resume_versions CASCADE")
