"""Trust & safety: job_risk (global), risk_overrides (tenant).

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "job_risk",
        sa.Column("job_id", _UUID, nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("score", sa.Float(), server_default="0", nullable=False),
        sa.Column("reasons", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("layers", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("model_version", sa.String(64), server_default="v1", nullable=False),
        sa.Column("partial", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "assessed_at",
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
        sa.PrimaryKeyConstraint("job_id", name="pk_job_risk"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_job_risk_job"
        ),
        sa.CheckConstraint(
            "level IN ('green','yellow','red')",
            name="ck_job_risk_level",
        ),
    )
    op.create_index("ix_job_risk_level", "job_risk", ["level"])
    op.execute("REVOKE ALL ON job_risk FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON job_risk TO kame_apply_app")

    op.create_table(
        "risk_overrides",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("job_id", _UUID, nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_risk_overrides"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_risk_overrides_ws",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="CASCADE", name="fk_risk_overrides_job"
        ),
        sa.UniqueConstraint("workspace_id", "job_id", name="uq_risk_overrides_ws_job"),
        sa.CheckConstraint(
            "decision IN ('continue','skip','reported','not_scam')",
            name="ck_risk_overrides_decision",
        ),
    )
    op.create_index(
        "ix_risk_overrides_workspace_decision",
        "risk_overrides",
        ["workspace_id", "decision"],
    )
    for stmt in tenant_rls_sql("risk_overrides"):
        op.execute(stmt)
    op.execute("REVOKE ALL ON risk_overrides FROM kame_apply_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON risk_overrides TO kame_apply_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS risk_overrides CASCADE")
    op.execute("DROP TABLE IF EXISTS job_risk CASCADE")
