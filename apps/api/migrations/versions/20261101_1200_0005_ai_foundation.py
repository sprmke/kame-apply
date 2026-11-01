"""ai: workspace_keys, ai_credentials, ai_settings, ai_usage

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_TABLES = ("workspace_keys", "ai_credentials", "ai_settings", "ai_usage")


def _ws_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["workspace_id"], ["workspaces.id"], ondelete="CASCADE",
        name=f"fk_{table}_workspace_id_workspaces",
    )


def upgrade() -> None:
    # Per-workspace data key, wrapped by the master key (KEK) from env.
    op.create_table(
        "workspace_keys",
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("wrapped_dek", sa.LargeBinary(), nullable=False),
        sa.Column("kek_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", name="pk_workspace_keys"),
        _ws_fk("workspace_keys"),
    )
    op.create_table(
        "ai_credentials",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("label", sa.String(80), nullable=True),
        sa.Column("encrypted_key", sa.LargeBinary(), nullable=True),
        sa.Column("key_hint", sa.String(8), nullable=True),
        sa.Column("base_url", sa.String(300), nullable=True),
        sa.Column("status", sa.String(12), server_default="untested", nullable=False),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", _UUID, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ai_credentials"),
        _ws_fk("ai_credentials"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_ai_credentials_created_by_users"),
        sa.CheckConstraint("provider IN ('gemini','openai','anthropic','groq','openrouter','ollama')", name="ck_ai_credentials_provider"),
        sa.CheckConstraint("status IN ('untested','valid','invalid')", name="ck_ai_credentials_status"),
    )
    op.create_index("ix_ai_credentials_workspace_id", "ai_credentials", ["workspace_id"])
    op.create_table(
        "ai_settings",
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("monthly_budget_cents", sa.Integer(), server_default="500", nullable=False),
        sa.Column("tier_models", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("fallback_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", name="pk_ai_settings"),
        _ws_fk("ai_settings"),
        sa.CheckConstraint("monthly_budget_cents >= 0", name="ck_ai_settings_budget"),
    )
    op.create_table(
        "ai_usage",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("credential_id", _UUID, nullable=True),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("tier", sa.String(12), nullable=False),
        sa.Column("feature", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_micros", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ai_usage"),
        _ws_fk("ai_usage"),
    )
    op.create_index("ix_ai_usage_workspace_created", "ai_usage", ["workspace_id", "created_at"])

    for t in _TABLES:
        for stmt in tenant_rls_sql(t):
            op.execute(stmt)
        op.execute(f"REVOKE ALL ON {t} FROM kame_apply_ro")
    # Usage is a ledger: append and read only.
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON ai_usage FROM kame_apply_app")


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.drop_table(t)
