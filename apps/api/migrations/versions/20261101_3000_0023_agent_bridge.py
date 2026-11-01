"""OAuth AS tables, agent_tasks, ai_feature_routing for Claude Agent Bridge.

Revision ID: 0023
Revises: 0022
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rls import tenant_rls_sql

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # OAuth clients are global (DCR); not tenant-scoped. Tokens/grants carry workspace_id.
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("client_secret_hash", sa.Text(), nullable=True),
        sa.Column("client_name", sa.Text(), server_default="", nullable=False),
        sa.Column("redirect_uris", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "grant_types",
            postgresql.JSONB(),
            server_default='["authorization_code","refresh_token"]',
            nullable=False,
        ),
        sa.Column("response_types", postgresql.JSONB(), server_default='["code"]', nullable=False),
        sa.Column("token_endpoint_auth_method", sa.Text(), server_default="none", nullable=False),
        sa.Column("scope", sa.Text(), server_default="", nullable=False),
        sa.Column("client_uri", sa.Text(), nullable=True),
        sa.Column("logo_uri", sa.Text(), nullable=True),
        sa.Column("contacts", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("tos_uri", sa.Text(), nullable=True),
        sa.Column("policy_uri", sa.Text(), nullable=True),
        sa.Column("jwks_uri", sa.Text(), nullable=True),
        sa.Column("jwks", postgresql.JSONB(), nullable=True),
        sa.Column("software_id", sa.Text(), nullable=True),
        sa.Column("software_version", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "oauth_pending_auths",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "client_id",
            sa.Text(),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column(
            "redirect_uri_provided_explicitly", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column("scopes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("code_challenge", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("resource", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_oauth_pending_auths_expires", "oauth_pending_auths", ["expires_at"])

    op.create_table(
        "oauth_auth_codes",
        sa.Column("code_hash", sa.Text(), primary_key=True),
        sa.Column(
            "client_id",
            sa.Text(),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
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
        sa.Column("scopes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("code_challenge", sa.Text(), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column(
            "redirect_uri_provided_explicitly", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column("resource", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


    # Auth codes: AS exchange has no workspace context; hash PK lookup only.
    from app.core.rls import WORKSPACE_EXPR as _WX_CODES
    op.execute("ALTER TABLE oauth_auth_codes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE oauth_auth_codes FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON oauth_auth_codes")
    op.execute(
        "CREATE POLICY tenant_isolation ON oauth_auth_codes "
        f"USING ("
        f"workspace_id = {_WX_CODES} "
        f"OR (NULLIF(current_setting('app.workspace_id', true), '') IS NULL "
        f"AND NULLIF(current_setting('app.user_id', true), '') IS NULL)"
        f") "
        f"WITH CHECK (workspace_id = {_WX_CODES} "
        f"OR (NULLIF(current_setting('app.workspace_id', true), '') IS NULL "
        f"AND NULLIF(current_setting('app.user_id', true), '') IS NULL))"
    )

    op.create_table(
        "oauth_tokens",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("token_kind", sa.Text(), nullable=False),  # access | refresh | pat
        sa.Column(
            "client_id",
            sa.Text(),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
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
        sa.Column("scopes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("resource", sa.Text(), nullable=True),
        sa.Column("refresh_family_id", _UUID, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_oauth_tokens_ws_user", "oauth_tokens", ["workspace_id", "user_id"])
    op.create_index("ix_oauth_tokens_hash", "oauth_tokens", ["token_hash"])
    # Token verify (OAuth AS) runs with no app.workspace_id; allow hash lookup only then.
    # List/revoke paths always set workspace context (tenant isolation).
    from app.core.rls import WORKSPACE_EXPR
    op.execute("ALTER TABLE oauth_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE oauth_tokens FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON oauth_tokens")
    op.execute(
        "CREATE POLICY tenant_isolation ON oauth_tokens "
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
        "agent_tasks",
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
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("input", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("output_schema", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("leased_by_client_id", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fallback_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('queued','leased','done','failed','expired')",
            name="ck_agent_tasks_status",
        ),
    )
    op.create_index(
        "ix_agent_tasks_lease",
        "agent_tasks",
        ["workspace_id", "status", "priority", "created_at"],
    )
    for stmt in tenant_rls_sql("agent_tasks"):
        op.execute(stmt)

    op.create_table(
        "ai_feature_routing",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("route", sa.Text(), server_default="server", nullable=False),
        sa.Column("fallback", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("workspace_id", "feature", name="uq_ai_feature_routing_ws_feature"),
        sa.CheckConstraint(
            "route IN ('server','agent_inbox')",
            name="ck_ai_feature_routing_route",
        ),
    )
    for stmt in tenant_rls_sql("ai_feature_routing"):
        op.execute(stmt)

    for table in (
        "oauth_clients",
        "oauth_pending_auths",
        "oauth_auth_codes",
        "oauth_tokens",
        "agent_tasks",
        "ai_feature_routing",
    ):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO kame_apply_app")


def downgrade() -> None:
    op.drop_table("ai_feature_routing")
    op.drop_table("agent_tasks")
    op.drop_table("oauth_tokens")
    op.drop_table("oauth_auth_codes")
    op.drop_table("oauth_pending_auths")
    op.drop_table("oauth_clients")
