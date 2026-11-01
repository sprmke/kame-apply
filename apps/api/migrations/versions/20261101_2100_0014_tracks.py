"""tracks, track_criteria, answer_bank.track_id FK, profile_skills.skill_id

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "tracks",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("profile_id", _UUID, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("icon", sa.String(64), server_default="ph:path", nullable=False),
        sa.Column("color_hue", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("autonomy", sa.String(16), server_default="discover", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("settings", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("template_slug", sa.String(80), nullable=True),
        sa.Column("created_by", _UUID, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_tracks"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_tracks_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_tracks_profile_id_candidate_profiles",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_tracks_created_by_users"),
        sa.CheckConstraint("status IN ('active','archived')", name="ck_tracks_status"),
        sa.CheckConstraint(
            "autonomy IN ('discover','prepare','assist','auto_submit')",
            name="ck_tracks_autonomy",
        ),
        sa.CheckConstraint("color_hue BETWEEN 1 AND 8", name="ck_tracks_color_hue"),
    )
    op.create_index(
        "ix_tracks_workspace_status_sort",
        "tracks",
        ["workspace_id", "status", "sort_order"],
    )
    for stmt in tenant_rls_sql("tracks"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON tracks FROM kame_apply_ro")

    op.create_table(
        "track_criteria",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=False),
        sa.Column("nl_text", sa.Text(), server_default="", nullable=False),
        sa.Column("structured", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("compiled", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_track_criteria"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_track_criteria_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
            name="fk_track_criteria_track_id_tracks",
        ),
        sa.UniqueConstraint("track_id", name="uq_track_criteria_track_id"),
    )
    for stmt in tenant_rls_sql("track_criteria"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON track_criteria FROM kame_apply_ro")

    # Phase 3 stored track_id without an FK; bind it now that tracks exist.
    op.execute("UPDATE answer_bank SET track_id = NULL WHERE track_id IS NOT NULL")
    op.create_foreign_key(
        "fk_answer_bank_track_id_tracks",
        "answer_bank",
        "tracks",
        ["track_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column(
        "profile_skills",
        sa.Column("skill_id", _UUID, nullable=True),
    )
    op.create_foreign_key(
        "fk_profile_skills_skill_id",
        "profile_skills",
        "taxonomy_skills",
        ["skill_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_profile_skills_skill_id", "profile_skills", type_="foreignkey"
    )
    op.drop_column("profile_skills", "skill_id")
    op.drop_constraint("fk_answer_bank_track_id_tracks", "answer_bank", type_="foreignkey")
    # Keep track_id column without FK for downgrade compatibility with 0010 shape.
    op.drop_table("track_criteria")
    op.drop_table("tracks")
