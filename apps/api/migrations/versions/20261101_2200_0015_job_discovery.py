"""Job discovery: sources, companies, boards, jobs, track links, runs.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("adapter", sa.String(64), nullable=False),
        sa.Column("terms_note", sa.Text(), server_default="", nullable=False),
        sa.Column("enabled_global", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("circuit_open", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("success_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("jobs_ingested", sa.Integer(), server_default="0", nullable=False),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("block_signals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("key", name="uq_sources_key"),
        sa.CheckConstraint(
            "kind IN ('ats','board','career_page','email','clip','personal')",
            name="ck_sources_kind",
        ),
    )
    op.execute("REVOKE ALL ON sources FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE ON sources TO kame_apply_app")

    op.create_table(
        "companies",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("normalized_name", sa.String(300), nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("favicon_url", sa.String(500), nullable=True),
        sa.Column("size", sa.String(64), nullable=True),
        sa.Column("industry", sa.String(120), nullable=True),
        sa.Column("aliases", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
    )
    op.create_index("ix_companies_normalized_name", "companies", ["normalized_name"])
    op.create_index("ix_companies_domain", "companies", ["domain"])
    op.execute("REVOKE ALL ON companies FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE ON companies TO kame_apply_app")

    op.create_table(
        "company_boards",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", _UUID, nullable=False),
        sa.Column("ats", sa.String(64), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("poll_tier", sa.String(16), server_default="cold", nullable=False),
        sa.Column("etag", sa.String(255), nullable=True),
        sa.Column("last_modified", sa.String(255), nullable=True),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_method", sa.String(64), server_default="seed", nullable=False),
        sa.Column("empty_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_boards"),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE", name="fk_company_boards_company"
        ),
        sa.UniqueConstraint("ats", "slug", name="uq_company_boards_ats_slug"),
        sa.CheckConstraint(
            "status IN ('active','inactive','pending')", name="ck_company_boards_status"
        ),
        sa.CheckConstraint(
            "poll_tier IN ('hot','warm','cold')", name="ck_company_boards_poll_tier"
        ),
    )
    op.create_index(
        "ix_company_boards_status_tier", "company_boards", ["status", "poll_tier", "last_polled_at"]
    )
    op.execute("REVOKE ALL ON company_boards FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE ON company_boards TO kame_apply_app")

    op.create_table(
        "jobs",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", _UUID, nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("normalized_title", sa.String(500), nullable=False),
        sa.Column(
            "occupation_codes", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("seniority", sa.String(64), nullable=True),
        sa.Column("employment_type", sa.String(64), nullable=True),
        sa.Column("work_mode", sa.String(32), nullable=True),
        sa.Column("locations", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("remote_eligibility", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("salary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("description_html", sa.Text(), server_default="", nullable=False),
        sa.Column("description_text", sa.Text(), server_default="", nullable=False),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("simhash", sa.BigInteger(), nullable=True),
        sa.Column("canonical_url", sa.String(1000), nullable=False),
        sa.Column("apply_url", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(16), server_default="open", nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("miss_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="SET NULL", name="fk_jobs_company"
        ),
        sa.CheckConstraint("status IN ('open','closed')", name="ck_jobs_status"),
    )
    op.create_index("ix_jobs_status_last_seen", "jobs", ["status", "last_seen_at"])
    op.create_index("ix_jobs_content_hash", "jobs", ["content_hash"])
    op.create_index("ix_jobs_company_title", "jobs", ["company_id", "normalized_title"])
    op.execute("REVOKE ALL ON jobs FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE ON jobs TO kame_apply_app")

    op.create_table(
        "job_sources",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", _UUID, nullable=False),
        sa.Column("source_id", _UUID, nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("board_id", _UUID, nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("raw", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_job_sources"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_job_sources_job"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], ondelete="CASCADE", name="fk_job_sources_source"
        ),
        sa.ForeignKeyConstraint(
            ["board_id"], ["company_boards.id"], ondelete="SET NULL", name="fk_job_sources_board"
        ),
        sa.UniqueConstraint("source_id", "external_id", name="uq_job_sources_source_external"),
    )
    op.create_index("ix_job_sources_job", "job_sources", ["job_id"])
    op.execute("REVOKE ALL ON job_sources FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE ON job_sources TO kame_apply_app")

    op.create_table(
        "country_source_registry",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("country", sa.String(8), nullable=False),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("coverage", sa.String(32), server_default="partial", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_country_source_registry"),
        sa.UniqueConstraint("country", "source_key", name="uq_country_source_registry"),
    )
    op.execute("REVOKE ALL ON country_source_registry FROM kame_apply_ro")
    op.execute("GRANT SELECT ON country_source_registry TO kame_apply_app")

    # Tenant tables
    op.create_table(
        "track_sources",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=False),
        sa.Column("source_id", _UUID, nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("params", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_track_sources"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_track_sources_ws"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_track_sources_track"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], ondelete="CASCADE", name="fk_track_sources_source"
        ),
        sa.UniqueConstraint("track_id", "source_id", name="uq_track_sources_track_source"),
    )
    op.create_index("ix_track_sources_workspace", "track_sources", ["workspace_id"])
    for stmt in tenant_rls_sql("track_sources"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON track_sources FROM kame_apply_ro")

    op.create_table(
        "track_jobs",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=False),
        sa.Column("job_id", _UUID, nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("fit", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("eligibility", sa.String(32), server_default="unknown", nullable=False),
        sa.Column("status", sa.String(32), server_default="new", nullable=False),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_track_jobs"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_track_jobs_ws"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_track_jobs_track"
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_track_jobs_job"
        ),
        sa.UniqueConstraint("track_id", "job_id", name="uq_track_jobs_track_job"),
        sa.CheckConstraint(
            "status IN ('new','shortlisted','skipped','hidden','applied')",
            name="ck_track_jobs_status",
        ),
    )
    op.create_index(
        "ix_track_jobs_workspace_track_status",
        "track_jobs",
        ["workspace_id", "track_id", "status"],
    )
    for stmt in tenant_rls_sql("track_jobs"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON track_jobs FROM kame_apply_ro")

    op.create_table(
        "discovery_runs",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=False),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("trigger", sa.String(32), server_default="manual", nullable=False),
        sa.Column("progress", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_runs"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_discovery_runs_ws"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_discovery_runs_track"
        ),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed','cancelled')",
            name="ck_discovery_runs_status",
        ),
    )
    op.create_index(
        "ix_discovery_runs_workspace_track",
        "discovery_runs",
        ["workspace_id", "track_id", "created_at"],
    )
    for stmt in tenant_rls_sql("discovery_runs"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON discovery_runs FROM kame_apply_ro")


def downgrade() -> None:
    for table in (
        "discovery_runs",
        "track_jobs",
        "track_sources",
        "country_source_registry",
        "job_sources",
        "jobs",
        "company_boards",
        "companies",
        "sources",
    ):
        op.drop_table(table)
