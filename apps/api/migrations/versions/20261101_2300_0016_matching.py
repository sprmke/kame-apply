"""Matching: qualifications, embeddings, hidden companies, track_job scoring fields.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "job_qualifications",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", _UUID, nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), server_default="", nullable=False),
        sa.Column("normalized", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_qualifications"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_job_qualifications_job"
        ),
        sa.CheckConstraint(
            "kind IN ('must','preferred','knockout')", name="ck_job_qualifications_kind"
        ),
    )
    op.create_index("ix_job_qualifications_job", "job_qualifications", ["job_id"])
    op.execute("REVOKE ALL ON job_qualifications FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON job_qualifications TO kame_apply_app")

    op.add_column("jobs", sa.Column("qualifications_hash", sa.String(64), nullable=True))
    op.add_column("jobs", sa.Column("embedding_model", sa.String(64), nullable=True))
    op.add_column(
        "jobs", sa.Column("few_stated_requirements", sa.Boolean(), server_default="false")
    )
    op.execute("ALTER TABLE jobs ADD COLUMN embedding vector(384)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_jobs_embedding_hnsw ON jobs "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    op.add_column(
        "track_jobs",
        sa.Column("score_components", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.add_column(
        "track_jobs",
        sa.Column("reasons", postgresql.JSONB(), server_default="[]", nullable=False),
    )
    op.add_column(
        "track_jobs",
        sa.Column("eligibility_detail", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.add_column(
        "track_jobs",
        sa.Column("last_scored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "track_jobs",
        sa.Column("ai_review_paused", sa.Boolean(), server_default="false", nullable=False),
    )

    op.create_table(
        "hidden_companies",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("company_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=True),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_hidden_companies"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_hidden_companies_ws",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
            name="fk_hidden_companies_company",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_hidden_companies_track"
        ),
        sa.UniqueConstraint(
            "workspace_id", "company_id", "track_id", name="uq_hidden_companies_scope"
        ),
    )
    op.create_index(
        "ix_hidden_companies_workspace", "hidden_companies", ["workspace_id", "company_id"]
    )
    for stmt in tenant_rls_sql("hidden_companies"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON hidden_companies FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON hidden_companies TO kame_apply_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hidden_companies CASCADE")
    op.drop_column("track_jobs", "ai_review_paused")
    op.drop_column("track_jobs", "last_scored_at")
    op.drop_column("track_jobs", "eligibility_detail")
    op.drop_column("track_jobs", "reasons")
    op.drop_column("track_jobs", "score_components")
    op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS embedding")
    op.drop_column("jobs", "few_stated_requirements")
    op.drop_column("jobs", "embedding_model")
    op.drop_column("jobs", "qualifications_hash")
    op.execute("DROP TABLE IF EXISTS job_qualifications CASCADE")
