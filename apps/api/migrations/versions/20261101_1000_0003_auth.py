"""auth: user_sessions, refresh_tokens, auth_tokens

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_sessions_user_id_users"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    # One row per issued refresh token. A token presented twice means theft: the session dies.
    op.create_table(
        "refresh_tokens",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", _UUID, nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(["session_id"], ["user_sessions.id"], ondelete="CASCADE", name="fk_refresh_tokens_session_id_user_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"])

    # Single-use emailed tokens (email verification, password reset). Only the hash is stored.
    op.create_table(
        "auth_tokens",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_auth_tokens"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_auth_tokens_user_id_users"),
        sa.UniqueConstraint("token_hash", name="uq_auth_tokens_token_hash"),
        sa.CheckConstraint("kind IN ('email_verify', 'password_reset')", name="ck_auth_tokens_kind"),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])

    # The read-only role (postgres MCP) must never see credentials or token hashes.
    op.execute("REVOKE ALL ON user_sessions, refresh_tokens, auth_tokens FROM kame_apply_ro")
    op.execute("REVOKE SELECT ON users FROM kame_apply_ro")
    op.execute(
        "GRANT SELECT (id, email, name, timezone, locale, email_verified_at, is_active, created_at) "
        "ON users TO kame_apply_ro"
    )


def downgrade() -> None:
    op.drop_table("auth_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("user_sessions")
    op.execute("GRANT SELECT ON users TO kame_apply_ro")
