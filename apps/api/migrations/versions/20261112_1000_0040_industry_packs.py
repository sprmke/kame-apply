"""Industry packs: workspace fields of work and per-track industry (IND-1).

Revision ID: 0040
Revises: 0039
Create Date: 2026-11-12

Backfill: every live workspace gets Technology as its primary field, and every track keeps the
Technology pack unless its template belongs to another field, which maps to General until that
curated pack ships. See docs/architecture/deployment.md.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "workspace_industries",
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("industry_key", sa.String(48), primary_key=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("custom_pack", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "uq_workspace_industries_primary",
        "workspace_industries",
        ["workspace_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    for stmt in tenant_rls_sql("workspace_industries"):
        op.execute(stmt)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON workspace_industries TO kame_apply_app"
    )

    op.add_column(
        "tracks",
        sa.Column("industry", sa.String(48), server_default="technology", nullable=False),
    )
    op.add_column(
        "tracks",
        sa.Column("industry_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_index("ix_tracks_industry", "tracks", ["workspace_id", "industry"])

    # Existing workspaces were all technology-shaped when this migration shipped.
    op.execute(
        """
        INSERT INTO workspace_industries (workspace_id, industry_key, is_primary)
        SELECT id, 'technology', true
        FROM workspaces
        WHERE deleted_at IS NULL
        ON CONFLICT DO NOTHING
        """
    )
    # A track built from a non-technology template belongs to General until its pack lands.
    op.execute(
        """
        UPDATE tracks AS t
        SET industry = CASE
            WHEN tt.industry = 'technology' THEN 'technology'
            ELSE 'general'
        END
        FROM track_templates AS tt
        WHERE t.template_slug = tt.slug
        """
    )


def downgrade() -> None:
    op.drop_index("ix_tracks_industry", table_name="tracks")
    op.drop_column("tracks", "industry_version")
    op.drop_column("tracks", "industry")
    op.drop_table("workspace_industries")
