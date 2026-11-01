"""Applications + cover letters for per-job tailoring.

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "cover_letters",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("profile_id", _UUID, nullable=False),
        sa.Column("job_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=True),
        sa.Column("resume_version_id", _UUID, nullable=True),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column("word_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("evidence_refs", postgresql.ARRAY(_UUID), server_default="{}", nullable=False),
        sa.Column("company_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_cover_letters"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_cover_letters_ws"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_cover_letters_profile",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_cover_letters_job"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="SET NULL", name="fk_cover_letters_track"
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
            name="fk_cover_letters_resume",
        ),
        sa.CheckConstraint(
            "status IN ('draft','accepted','discarded')", name="ck_cover_letters_status"
        ),
    )
    for stmt in tenant_rls_sql("cover_letters"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON cover_letters FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON cover_letters TO kame_apply_app")

    op.create_table(
        "applications",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=False),
        sa.Column("job_id", _UUID, nullable=False),
        sa.Column("track_job_id", _UUID, nullable=True),
        sa.Column("profile_id", _UUID, nullable=False),
        sa.Column("status", sa.String(32), server_default="ready", nullable=False),
        sa.Column("method", sa.String(32), server_default="manual", nullable=False),
        sa.Column("resume_version_id", _UUID, nullable=True),
        sa.Column("cover_letter_id", _UUID, nullable=True),
        sa.Column("job_snapshot_r2", sa.String(500), nullable=True),
        sa.Column("lens_before", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("lens_after", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_applications"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_applications_ws"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_applications_track"
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_applications_job"
        ),
        sa.ForeignKeyConstraint(
            ["track_job_id"],
            ["track_jobs.id"],
            ondelete="SET NULL",
            name="fk_applications_track_job",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_applications_profile",
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
            name="fk_applications_resume",
        ),
        sa.ForeignKeyConstraint(
            ["cover_letter_id"],
            ["cover_letters.id"],
            ondelete="SET NULL",
            name="fk_applications_cover",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'draft','ready','applied','responded','interview','offer',"
            "'rejected','withdrawn','job_closed')",
            name="ck_applications_status",
        ),
        sa.CheckConstraint(
            "method IN ('extension','runner','manual','answer_desk')",
            name="ck_applications_method",
        ),
        sa.UniqueConstraint(
            "workspace_id", "track_id", "job_id", name="uq_applications_ws_track_job"
        ),
    )
    op.create_index(
        "ix_applications_workspace_status",
        "applications",
        ["workspace_id", "status"],
    )
    for stmt in tenant_rls_sql("applications"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON applications FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON applications TO kame_apply_app")

    op.create_table(
        "tailor_runs",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("track_job_id", _UUID, nullable=False),
        sa.Column("job_id", _UUID, nullable=False),
        sa.Column("track_id", _UUID, nullable=False),
        sa.Column("profile_id", _UUID, nullable=False),
        sa.Column("base_version_id", _UUID, nullable=True),
        sa.Column("draft_version_id", _UUID, nullable=True),
        sa.Column("cover_letter_id", _UUID, nullable=True),
        sa.Column("status", sa.String(24), server_default="running", nullable=False),
        sa.Column("lens_before", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("lens_after", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("gaps", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("knockouts", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("proposed_changes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("progress", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("error", sa.Text(), server_default="", nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_tailor_runs"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE", name="fk_tailor_runs_ws"
        ),
        sa.ForeignKeyConstraint(
            ["track_job_id"],
            ["track_jobs.id"],
            ondelete="CASCADE",
            name="fk_tailor_runs_track_job",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_tailor_runs_job"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], ondelete="CASCADE", name="fk_tailor_runs_track"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_tailor_runs_profile",
        ),
        sa.CheckConstraint(
            "status IN ('running','ready','accepted','discarded','failed')",
            name="ck_tailor_runs_status",
        ),
    )
    for stmt in tenant_rls_sql("tailor_runs"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON tailor_runs FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON tailor_runs TO kame_apply_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tailor_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS applications CASCADE")
    op.execute("DROP TABLE IF EXISTS cover_letters CASCADE")
