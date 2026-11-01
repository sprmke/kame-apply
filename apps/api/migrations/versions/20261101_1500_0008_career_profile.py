"""career profile: candidate_profiles and the fact sections

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLES = (
    "candidate_profiles",
    "profile_experiences",
    "profile_projects",
    "profile_bullets",
    "profile_education",
    "profile_certifications",
    "profile_languages",
    "profile_skills",
)
_SOURCES = "('parsed','interview','user')"


def _id() -> sa.Column:
    return sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False)


def _ws(table: str) -> list:
    return [
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE",
            name=f"fk_{table}_workspace_id_workspaces",
        ),
    ]


def _profile_fk(table: str) -> list:
    return [
        sa.Column("profile_id", _UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["candidate_profiles.id"], ondelete="CASCADE",
            name=f"fk_{table}_profile_id_candidate_profiles",
        ),
    ]


def _tail() -> list:
    now = sa.func.now()
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    ]


def _flags() -> list:
    return [
        sa.Column("do_not_use", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("confidential", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source", sa.String(12), server_default="user", nullable=False),
    ]


def _table(name: str, *cols, checks: tuple = ()) -> None:
    op.create_table(
        name,
        _id(),
        *_ws(name),
        *_profile_fk(name),
        *cols,
        *_tail(),
        sa.PrimaryKeyConstraint("id", name=f"pk_{name}"),
        sa.CheckConstraint(f"source IN {_SOURCES}", name=f"ck_{name}_source"),
        *checks,
    )
    op.create_index(f"ix_{name}_workspace_profile", name, ["workspace_id", "profile_id"])


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        _id(),
        *_ws("candidate_profiles"),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("headline", sa.String(300), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("language", sa.String(16), server_default="en", nullable=False),
        sa.Column("work_authorization", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("salary_prefs", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("links", postgresql.JSONB(), server_default="[]", nullable=False),
        # Data minimization: photo, date of birth and full address stay out unless switched on.
        sa.Column("minimization", postgresql.JSONB(),
                  server_default='{"photo": false, "dob": false, "full_address": false}', nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_by", _UUID, nullable=True),
        *_tail(),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_profiles"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_candidate_profiles_created_by_users"),
    )
    op.create_index("ix_candidate_profiles_workspace", "candidate_profiles", ["workspace_id"])
    op.create_index(
        "uq_candidate_profiles_default", "candidate_profiles", ["workspace_id"],
        unique=True, postgresql_where=sa.text("is_default"),
    )

    _table(
        "profile_experiences",
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("employment_type", sa.String(24), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_flags(),
        checks=(
            sa.CheckConstraint(
                "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
                name="ck_profile_experiences_dates",
            ),
        ),
    )
    _table(
        "profile_projects",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        *_flags(),
    )
    _table(
        "profile_bullets",
        sa.Column("experience_id", _UUID, nullable=True),
        sa.Column("project_id", _UUID, nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.String(80)), server_default="{}", nullable=False),
        sa.Column("evidence_strength", sa.String(8), server_default="weak", nullable=False),
        *_flags(),
        sa.ForeignKeyConstraint(
            ["experience_id"], ["profile_experiences.id"], ondelete="CASCADE",
            name="fk_profile_bullets_experience_id",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["profile_projects.id"], ondelete="CASCADE",
            name="fk_profile_bullets_project_id",
        ),
        checks=(
            sa.CheckConstraint(
                "num_nonnulls(experience_id, project_id) = 1", name="ck_profile_bullets_one_parent"
            ),
            sa.CheckConstraint(
                "evidence_strength IN ('weak','ok','strong')", name="ck_profile_bullets_strength"
            ),
        ),
    )
    _table(
        "profile_education",
        sa.Column("institution", sa.String(200), nullable=False),
        sa.Column("degree", sa.String(200), nullable=True),
        sa.Column("field", sa.String(200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_flags(),
    )
    _table(
        "profile_certifications",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("issuer", sa.String(200), nullable=True),
        sa.Column("kind", sa.String(12), server_default="certification", nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("jurisdiction", sa.String(120), nullable=True),
        *_flags(),
        checks=(
            sa.CheckConstraint(
                "kind IN ('certification','license')", name="ck_profile_certifications_kind"
            ),
        ),
    )
    _table(
        "profile_languages",
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("proficiency", sa.String(16), nullable=True),
        *_flags(),
    )
    _table(
        "profile_skills",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("level", sa.String(16), nullable=True),
        sa.Column("years", sa.Numeric(4, 1), nullable=True),
        sa.Column("last_used", sa.Integer(), nullable=True),
        # Skill normalization against the taxonomy lands in Phase 4; raw names until then.
        sa.Column("evidence_refs", postgresql.ARRAY(_UUID), server_default="{}", nullable=False),
        *_flags(),
    )

    for t in _TABLES:
        for stmt in tenant_rls_sql(t):
            op.execute(stmt)
        op.execute(f"REVOKE ALL ON {t} FROM kame_apply_ro")


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.drop_table(t)
