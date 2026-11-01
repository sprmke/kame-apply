"""global taxonomy, currency rates, track templates, geocode cache

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "taxonomy_occupations",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("scheme", sa.String(16), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("isco_code", sa.String(16), nullable=True),
        sa.Column("labels", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("alt_titles", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_taxonomy_occupations"),
        sa.UniqueConstraint("scheme", "code", name="uq_taxonomy_occupations_scheme_code"),
        sa.CheckConstraint(
            "scheme IN ('esco','onet','isco','soc')", name="ck_taxonomy_occupations_scheme"
        ),
    )
    op.execute("ALTER TABLE taxonomy_occupations ADD COLUMN embedding vector(384)")
    op.execute(
        "CREATE INDEX ix_taxonomy_occupations_label_trgm ON taxonomy_occupations "
        "USING gin (label gin_trgm_ops)"
    )

    op.create_table(
        "taxonomy_skills",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("scheme", sa.String(16), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("skill_type", sa.String(32), nullable=True),
        sa.Column("labels", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("aliases", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_taxonomy_skills"),
        sa.UniqueConstraint("scheme", "code", name="uq_taxonomy_skills_scheme_code"),
        sa.CheckConstraint("scheme IN ('esco','onet')", name="ck_taxonomy_skills_scheme"),
    )
    op.execute("ALTER TABLE taxonomy_skills ADD COLUMN embedding vector(384)")
    op.execute(
        "CREATE INDEX ix_taxonomy_skills_label_trgm ON taxonomy_skills "
        "USING gin (label gin_trgm_ops)"
    )

    op.create_table(
        "taxonomy_occupation_skills",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("occupation_id", _UUID, nullable=False),
        sa.Column("skill_id", _UUID, nullable=False),
        sa.Column("relation", sa.String(24), server_default="essential", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_taxonomy_occupation_skills"),
        sa.ForeignKeyConstraint(
            ["occupation_id"],
            ["taxonomy_occupations.id"],
            ondelete="CASCADE",
            name="fk_tax_occ_skills_occupation_id",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["taxonomy_skills.id"],
            ondelete="CASCADE",
            name="fk_tax_occ_skills_skill_id",
        ),
        sa.UniqueConstraint(
            "occupation_id", "skill_id", "relation", name="uq_taxonomy_occ_skill_rel"
        ),
        sa.CheckConstraint(
            "relation IN ('essential','optional')", name="ck_taxonomy_occupation_skills_relation"
        ),
    )

    op.create_table(
        "taxonomy_crosswalks",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("from_scheme", sa.String(16), nullable=False),
        sa.Column("from_code", sa.String(64), nullable=False),
        sa.Column("to_scheme", sa.String(16), nullable=False),
        sa.Column("to_code", sa.String(64), nullable=False),
        sa.Column("confidence", sa.String(16), server_default="exact", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_taxonomy_crosswalks"),
        sa.UniqueConstraint(
            "from_scheme",
            "from_code",
            "to_scheme",
            "to_code",
            name="uq_taxonomy_crosswalk",
        ),
    )

    op.create_table(
        "taxonomy_aliases",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("alias", sa.String(200), nullable=False),
        sa.Column("alias_key", sa.String(200), nullable=False),
        sa.Column("canonical", sa.String(300), nullable=False),
        sa.Column("skill_id", _UUID, nullable=True),
        sa.Column("occupation_id", _UUID, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_taxonomy_aliases"),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["taxonomy_skills.id"],
            ondelete="SET NULL",
            name="fk_tax_aliases_skill_id",
        ),
        sa.ForeignKeyConstraint(
            ["occupation_id"],
            ["taxonomy_occupations.id"],
            ondelete="SET NULL",
            name="fk_tax_aliases_occupation_id",
        ),
        sa.UniqueConstraint("kind", "alias_key", name="uq_taxonomy_aliases_kind_key"),
        sa.CheckConstraint("kind IN ('skill','title')", name="ck_taxonomy_aliases_kind"),
    )
    op.execute(
        "CREATE INDEX ix_taxonomy_aliases_alias_trgm ON taxonomy_aliases "
        "USING gin (alias gin_trgm_ops)"
    )

    op.create_table(
        "currency_rates",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("as_of", sa.String(10), nullable=False),
        sa.Column("base", sa.String(3), server_default="USD", nullable=False),
        sa.Column("rates", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("source", sa.String(32), server_default="fallback", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_currency_rates"),
    )
    op.create_index("ix_currency_rates_as_of", "currency_rates", ["as_of"])

    op.create_table(
        "track_templates",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("icon", sa.String(64), server_default="ph:path", nullable=False),
        sa.Column("color_hue", sa.Integer(), server_default="1", nullable=False),
        sa.Column("criteria", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("nl_seed", sa.Text(), server_default="", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_track_templates"),
        sa.UniqueConstraint("slug", name="uq_track_templates_slug"),
        sa.CheckConstraint("color_hue BETWEEN 1 AND 8", name="ck_track_templates_color_hue"),
    )
    op.create_index("ix_track_templates_industry", "track_templates", ["industry"])

    op.create_table(
        "geocode_cache",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("query_key", sa.String(300), nullable=False),
        sa.Column("query", sa.String(300), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("raw", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_geocode_cache"),
        sa.UniqueConstraint("query_key", name="uq_geocode_cache_query_key"),
    )

    # Global reference data: tenants may read; writes are owner/refresh only.
    for t in (
        "taxonomy_occupations",
        "taxonomy_skills",
        "taxonomy_occupation_skills",
        "taxonomy_crosswalks",
        "taxonomy_aliases",
        "currency_rates",
        "track_templates",
        "geocode_cache",
    ):
        op.execute(f"REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON {t} FROM kame_apply_app")
        op.execute(f"REVOKE ALL ON {t} FROM kame_apply_ro")
        op.execute(f"GRANT SELECT ON {t} TO kame_apply_app")
        op.execute(f"GRANT SELECT ON {t} TO kame_apply_ro")

    # Geocode cache: app may insert on miss (still no update/delete of others' rows needed).
    op.execute("GRANT INSERT ON geocode_cache TO kame_apply_app")


def downgrade() -> None:
    for t in (
        "geocode_cache",
        "track_templates",
        "currency_rates",
        "taxonomy_aliases",
        "taxonomy_crosswalks",
        "taxonomy_occupation_skills",
        "taxonomy_skills",
        "taxonomy_occupations",
    ):
        op.drop_table(t)
