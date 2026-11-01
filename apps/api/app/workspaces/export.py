"""Workspace data export (JSON). Omits secrets, tokens, and encrypted credential material."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.core.security import WorkspaceContext


def _row(mapping: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in dict(mapping).items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, UUID):
            out[k] = str(v)
        elif isinstance(v, (bytes, memoryview)):
            out[k] = "<binary omitted>"
        else:
            out[k] = v
    return out


async def _table_rows(ctx: WorkspaceContext, sql: str, params: dict | None = None) -> list[dict]:
    result = await ctx.session.execute(text(sql), params or {})
    return [_row(r) for r in result.mappings().all()]


async def build_export(ctx: WorkspaceContext) -> dict[str, Any]:
    """Assemble a portable JSON export of workspace-owned data (no secrets)."""
    wid = str(ctx.workspace_id)
    ws = (
        await _table_rows(
            ctx,
            "SELECT id, name, kind, created_at FROM workspaces WHERE id = CAST(:wid AS uuid)",
            {"wid": wid},
        )
    )[0]

    # Literals only; RLS still scopes tenant tables when app.workspace_id is set.
    tables_star = [
        "tracks",
        "track_criteria",
        "schedules",
        "candidate_profiles",
        "profile_experiences",
        "profile_projects",
        "profile_bullets",
        "profile_education",
        "profile_certifications",
        "profile_languages",
        "profile_skills",
        "answer_bank",
        "voice_profiles",
        "jobs",
        "track_jobs",
        "applications",
        "application_events",
        "cover_letters",
        "answer_desk_sessions",
        "answer_desk_items",
        "notifications",
        "resume_versions",
        "documents",
    ]
    payload: dict[str, Any] = {
        "exported_at": datetime.now(UTC).isoformat(),
        "format_version": 1,
        "workspace": ws,
        "members": await _table_rows(
            ctx, "SELECT user_id, role, is_active, created_at FROM workspace_members"
        ),
        "ai_credentials_meta": await _table_rows(
            ctx,
            "SELECT id, provider, label, key_hint, base_url, status, last_tested_at, created_at "
            "FROM ai_credentials",
        ),
        "ai_settings": await _table_rows(
            ctx, "SELECT monthly_budget_cents, tier_models, fallback_enabled FROM ai_settings"
        ),
        "activity_log": await _table_rows(
            ctx,
            "SELECT id, actor_type, actor_id, action, target_type, target_id, created_at "
            "FROM activity_log",
        ),
        "notes": {
            "omitted": [
                "refresh_tokens",
                "auth_tokens",
                "extension_tokens",
                "oauth_tokens",
                "ai_credentials.encrypted_key",
                "workspace_keys",
                "R2 object bytes (keys listed under documents / resume_versions)",
            ]
        },
    }
    for table in tables_star:
        payload[table] = await _table_rows(ctx, f"SELECT * FROM {table}")  # noqa: S608
    return payload


def export_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, default=str).encode("utf-8")
