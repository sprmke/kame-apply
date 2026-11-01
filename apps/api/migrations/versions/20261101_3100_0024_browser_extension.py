"""Extension tokens, platform policies, apply runs, form signatures (Phase 13).

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import WORKSPACE_EXPR, tenant_rls_sql

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "extension_tokens",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("label", sa.Text(), server_default="browser", nullable=False),
        sa.Column("scopes", postgresql.JSONB(), server_default='["extension"]', nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_extension_tokens_ws_user", "extension_tokens", ["workspace_id", "user_id"])
    # AS-style: hash lookup may run before workspace context is set on the request.
    op.execute("ALTER TABLE extension_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE extension_tokens FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON extension_tokens")
    op.execute(
        "CREATE POLICY tenant_isolation ON extension_tokens "
        f"USING ("
        f"workspace_id = {WORKSPACE_EXPR} "
        f"OR (NULLIF(current_setting('app.workspace_id', true), '') IS NULL "
        f"AND NULLIF(current_setting('app.user_id', true), '') IS NULL)"
        f") "
        f"WITH CHECK (workspace_id = {WORKSPACE_EXPR} "
        f"OR (NULLIF(current_setting('app.workspace_id', true), '') IS NULL "
        f"AND NULLIF(current_setting('app.user_id', true), '') IS NULL))"
    )

    op.create_table(
        "workspace_platform_policies",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("autofill_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("terms_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("workspace_id", "platform", name="uq_ws_platform_policy"),
        sa.CheckConstraint(
            "platform IN ('linkedin','indeed','jobstreet','seek','greenhouse','lever',"
            "'ashby','workday','workable','smartrecruiters','generic')",
            name="ck_platform_policy_platform",
        ),
    )
    for stmt in tenant_rls_sql("workspace_platform_policies"):
        op.execute(stmt)

    # Global form signature cache: label→canonical key only (never values).
    op.create_table(
        "form_signatures",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("signature_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("ats", sa.Text(), server_default="generic", nullable=False),
        sa.Column("field_map", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "apply_runs",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            _UUID,
            sa.ForeignKey("applications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("job_id", _UUID, sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "track_id", _UUID, sa.ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "profile_id",
            _UUID,
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.Text(), server_default="extension", nullable=False),
        sa.Column("platform", sa.Text(), server_default="generic", nullable=False),
        sa.Column("page_url", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.Text(), server_default="running", nullable=False),
        sa.Column("created_by", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('queued','running','needs_you','paused','completed','failed','cancelled')",
            name="ck_apply_runs_status",
        ),
        sa.CheckConstraint(
            "source IN ('extension','runner')",
            name="ck_apply_runs_source",
        ),
    )
    op.create_index("ix_apply_runs_ws_status", "apply_runs", ["workspace_id", "status"])
    for stmt in tenant_rls_sql("apply_runs"):
        op.execute(stmt)

    op.create_table(
        "apply_run_steps",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id", _UUID, sa.ForeignKey("apply_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("page_url", sa.Text(), server_default="", nullable=False),
        sa.Column("action", sa.Text(), server_default="fill", nullable=False),
        sa.Column("field_label", sa.Text(), server_default="", nullable=False),
        sa.Column("value_redacted", sa.Text(), server_default="", nullable=False),
        sa.Column("canonical_key", sa.Text(), nullable=True),
        sa.Column("source_fact_ref", sa.Text(), nullable=True),
        sa.Column("pii_class", sa.Text(), server_default="personal", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_apply_run_steps_run", "apply_run_steps", ["run_id", "seq"])
    for stmt in tenant_rls_sql("apply_run_steps"):
        op.execute(stmt)

    for table in (
        "extension_tokens",
        "workspace_platform_policies",
        "form_signatures",
        "apply_runs",
        "apply_run_steps",
    ):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO kame_apply_app")


def downgrade() -> None:
    op.drop_table("apply_run_steps")
    op.drop_table("apply_runs")
    op.drop_table("form_signatures")
    op.drop_table("workspace_platform_policies")
    op.drop_table("extension_tokens")
