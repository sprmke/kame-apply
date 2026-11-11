from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Fail closed: an unset ENVIRONMENT means production, so a deploy that forgets it refuses to
    # start with the public dev secrets instead of running with them. Local dev sets local in .env.
    environment: Literal["local", "dev", "prod", "test"] = "prod"
    log_level: str = "INFO"
    log_json: bool = True

    # Runtime URL: must be a role WITHOUT BYPASSRLS (kame_apply_app locally) so RLS applies.
    database_url: str = (
        "postgresql+asyncpg://kame_apply_app:kame_apply_app_local_only@127.0.0.1:5442/kame_apply"
    )
    # Owner/migration role; used by Alembic only (MIGRATION_DATABASE_URL env overrides).
    migration_database_url: str = (
        "postgresql+asyncpg://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply"
    )
    db_pool_size: int = Field(default=10, ge=1)
    db_echo: bool = False

    cors_origins: list[str] = ["http://localhost:3100"]
    web_base_url: str = "http://localhost:3100"
    api_base_url: str = "http://localhost:8100"  # used to build the OAuth redirect URI
    google_client_id: str | None = None
    google_client_secret: str | None = None

    # Phase 12b Claude Agent Bridge (MCP). Never store Claude credentials here.
    agent_bridge_enabled: bool = True

    # Auth. The default secret is for local/test only; prod refuses to start with it.
    jwt_secret: str = "dev-only-jwt-secret-change-me-0123456789abcdef"  # noqa: S105
    access_token_ttl_seconds: int = 15 * 60
    refresh_token_ttl_seconds: int = 30 * 24 * 3600
    email_verify_ttl_seconds: int = 48 * 3600
    password_reset_ttl_seconds: int = 3600
    cookie_secure: bool = False  # True in prod (HTTPS only)
    auth_rate_limit_enabled: bool = True

    # Master key (base64, 32 bytes) wrapping per-workspace data keys. Local default is public;
    # prod refuses it. Generate: python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
    master_kek: str = "ZGV2LW9ubHktbWFzdGVyLWtleS0wMTIzNDU2Nzg5YWI="
    ai_max_output_tokens: int = 1024

    # Mail: SMTP (Mailpit locally) or Resend when RESEND_API_KEY is set.
    mail_from: str = "Kame Apply <no-reply@kame-apply.local>"
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1125
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    smtp_ssl: bool = False
    resend_api_key: str | None = None
    sentry_dsn: str | None = None

    # Comma-separated IPs/CIDRs allowed to set X-Forwarded-For / X-Real-IP (Caddy in prod).
    trusted_proxies: str = ""

    # Beta feedback → GitHub issue (optional; without token, feedback is audit-logged only).
    github_feedback_token: str | None = None
    github_feedback_repo: str = "kame-hq/kame-apply"

    # Object storage (Cloudflare R2; MinIO locally). Tests use an in-memory store.
    s3_endpoint_url: str | None = "http://127.0.0.1:9100"
    # Browser-facing endpoint for presigned URLs. Defaults to s3_endpoint_url.
    s3_public_endpoint_url: str | None = None
    s3_access_key: str = "kame_apply"
    s3_secret_key: str = "kame_apply_local_only"  # noqa: S105
    s3_bucket: str = "kame-apply"
    s3_region: str = "auto"

    # Phase 17: inbound email alerts, web push, Telegram
    inbound_email_domain: str = "in.kameapply.local"
    inbound_webhook_secret: str | None = None
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:ops@kameapply.local"
    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = None
    telegram_webhook_secret: str | None = None
    gmail_listener_enabled: bool = False
    # Phase 19: global kill for auto-submit (off by default until go/no-go).
    auto_submit_enabled: bool = False
    # Phase 10/14: in-process minute scheduler for due Track schedules (dev/prod only).
    scheduler_enabled: bool = True

    @property
    def trusted_proxy_networks(self) -> list[str]:
        return [p.strip() for p in self.trusted_proxies.split(",") if p.strip()]

    @model_validator(mode="after")
    def _prod_requires_real_secrets(self) -> "Settings":
        import base64

        try:
            kek = base64.b64decode(self.master_kek)
        except Exception as exc:
            raise ValueError("MASTER_KEK must be valid base64") from exc
        if len(kek) != 32:
            raise ValueError("MASTER_KEK must decode to exactly 32 bytes")
        if self.environment == "prod":
            if self.jwt_secret.startswith("dev-only") or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be set to a strong value in prod")
            if self.master_kek.startswith("ZGV2LW9ubHk"):
                raise ValueError("MASTER_KEK must be set to a private key in prod")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in prod")
            if self.telegram_bot_token and not self.telegram_webhook_secret:
                raise ValueError(
                    "TELEGRAM_WEBHOOK_SECRET must be set when the Telegram bot is enabled"
                )
        return self

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
