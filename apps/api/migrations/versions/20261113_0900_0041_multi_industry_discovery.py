"""Multi-industry discovery: industry hints, query cache, coverage, profile facets.

Revision ID: 0041
Revises: 0040
Create Date: 2026-11-13

Adds the global discovery tables and the tenant `profile_facets` table. Existing rows are
Technology because every job, board, and company came from the tech-shaped discovery path.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TEXT_ARRAY = postgresql.ARRAY(sa.Text())


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("industries", _TEXT_ARRAY, server_default="{}", nullable=False),
    )
    op.add_column(
        "company_boards",
        sa.Column("industries", _TEXT_ARRAY, server_default="{}", nullable=False),
    )
    op.add_column(
        "jobs",
        sa.Column("industry_hints", _TEXT_ARRAY, server_default="{}", nullable=False),
    )
    op.add_column("jobs", sa.Column("occupation_code", sa.String(32), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("facets", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.add_column(
        "profile_certifications", sa.Column("credential_key", sa.String(64), nullable=True)
    )

    op.drop_constraint("ck_sources_kind", "sources", type_="check")
    op.create_check_constraint(
        "ck_sources_kind",
        "sources",
        "kind IN ('ats','board','career_page','email','clip','personal','search')",
    )

    op.create_index("ix_jobs_industry_hints", "jobs", ["industry_hints"], postgresql_using="gin")
    op.create_index(
        "ix_companies_industries", "companies", ["industries"], postgresql_using="gin"
    )
    op.create_index(
        "ix_company_boards_industries",
        "company_boards",
        ["industries"],
        postgresql_using="gin",
    )

    op.create_table(
        "source_coverage",
        sa.Column("source_key", sa.String(64), primary_key=True),
        sa.Column("country", sa.String(8), primary_key=True),
        sa.Column("industry", sa.String(48), primary_key=True),
        sa.Column("coverage", sa.String(16), server_default="thin", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "coverage IN ('strong','partial','thin','none')", name="ck_source_coverage_level"
        ),
    )
    op.create_table(
        "source_query_cache",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("query_hash", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("source_key", "query_hash", name="uq_source_query_cache"),
    )
    op.create_index(
        "ix_source_query_cache_expires", "source_query_cache", ["expires_at"]
    )

    op.create_table(
        "profile_facets",
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
        sa.Column("facet_key", sa.String(48), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(16), server_default="user", nullable=False),
        sa.Column("do_not_use", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("confidential", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("profile_id", "facet_key", "value", name="uq_profile_facet_value"),
        sa.CheckConstraint("source IN ('user', 'parsed', 'interview')", name="ck_profile_facet_source"),
    )
    op.create_index("ix_profile_facets_profile", "profile_facets", ["profile_id", "facet_key"])
    for stmt in tenant_rls_sql("profile_facets"):
        op.execute(stmt)

    for table in ("source_coverage", "source_query_cache"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO kame_apply_app")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON profile_facets TO kame_apply_app"
    )

    # Existing data is tech-shaped.
    op.execute("UPDATE companies SET industries = ARRAY['technology']")
    op.execute("UPDATE company_boards SET industries = ARRAY['technology']")
    op.execute("UPDATE jobs SET industry_hints = ARRAY['technology']")

    # Honest starting coverage. IND-4 verifies live quotas and terms before an adapter runs.
    op.execute(
        """
        INSERT INTO source_coverage (source_key, country, industry, coverage, note) VALUES
          ('remotive','REMOTE','technology','strong','Remote tech roles'),
          ('remoteok','REMOTE','technology','strong','Remote tech roles'),
          ('himalayas','REMOTE','technology','strong','Remote tech roles'),
          ('muse','US','technology','partial','US-heavy'),
          ('arbeitnow','DE','technology','strong','EU/DE'),
          ('arbeitnow','EU','technology','partial','EU'),
          ('career_jsonld','GLOBAL','technology','partial','Employer career pages via JobPosting markup'),
          ('search_jooble','PH','hospitality','partial','Keyword and location search; terms pending verification'),
          ('search_jooble','AE','hospitality','partial','Keyword and location search; terms pending verification'),
          ('search_jooble','PH','technology','partial','Keyword and location search; terms pending verification'),
          ('search_jooble','AE','technology','partial','Keyword and location search; terms pending verification'),
          ('search_adzuna','GB','technology','partial','Adzuna API; quota and attribution pending verification'),
          ('search_adzuna','US','technology','partial','Adzuna API; quota and attribution pending verification'),
          ('culinary_agents','GLOBAL','hospitality','partial','Guided email alerts only; no server-side scrape')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM sources WHERE kind = 'search'")
    op.drop_constraint("ck_sources_kind", "sources", type_="check")
    op.create_check_constraint(
        "ck_sources_kind",
        "sources",
        "kind IN ('ats','board','career_page','email','clip','personal')",
    )
    op.drop_table("profile_facets")
    op.drop_index("ix_source_query_cache_expires", table_name="source_query_cache")
    op.drop_table("source_query_cache")
    op.drop_table("source_coverage")
    op.drop_index("ix_company_boards_industries", table_name="company_boards")
    op.drop_index("ix_companies_industries", table_name="companies")
    op.drop_index("ix_jobs_industry_hints", table_name="jobs")
    op.drop_column("profile_certifications", "credential_key")
    op.drop_column("jobs", "facets")
    op.drop_column("jobs", "occupation_code")
    op.drop_column("jobs", "industry_hints")
    op.drop_column("company_boards", "industries")
    op.drop_column("companies", "industries")
