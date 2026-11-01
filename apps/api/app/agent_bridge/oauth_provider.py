"""Postgres-backed MCP OAuth authorization server provider."""

# ruff: noqa: S105,S106

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl, AnyUrl
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent_bridge.models import (
    OAuthAuthCode,
    OAuthClient,
    OAuthPendingAuth,
)
from app.agent_bridge.models import (
    OAuthToken as OAuthTokenRow,
)
from app.agent_bridge.scopes import ALL_SCOPES
from app.agent_bridge.tokens import hash_token, new_token, subject_for
from app.core.config import Settings
from app.core.rls import set_request_context

logger = logging.getLogger(__name__)

ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=30)
CODE_TTL = timedelta(minutes=10)
PENDING_TTL = timedelta(minutes=15)


class KameOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    def __init__(
        self, *, session_factory: async_sessionmaker[AsyncSession], settings: Settings
    ) -> None:
        self._sf = session_factory
        self._settings = settings

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        async with self._sf() as session:
            row = await session.get(OAuthClient, client_id)
            if row is None:
                return None
            return _to_client_info(row)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        async with self._sf() as session, session.begin():
            existing = await session.get(OAuthClient, client_info.client_id)
            if existing is not None:
                return
            secret_hash = None
            if client_info.client_secret:
                secret_hash = hash_token(client_info.client_secret)
            session.add(
                OAuthClient(
                    id=client_info.client_id,
                    client_secret_hash=secret_hash,
                    client_name=client_info.client_name or "",
                    redirect_uris=[str(u) for u in (client_info.redirect_uris or [])],
                    grant_types=list(
                        client_info.grant_types or ["authorization_code", "refresh_token"]
                    ),
                    response_types=list(client_info.response_types or ["code"]),
                    token_endpoint_auth_method=client_info.token_endpoint_auth_method or "none",
                    scope=client_info.scope or " ".join(ALL_SCOPES),
                    client_uri=str(client_info.client_uri) if client_info.client_uri else None,
                    logo_uri=str(client_info.logo_uri) if client_info.logo_uri else None,
                    contacts=list(client_info.contacts or []),
                    tos_uri=str(client_info.tos_uri) if client_info.tos_uri else None,
                    policy_uri=str(client_info.policy_uri) if client_info.policy_uri else None,
                    jwks_uri=str(client_info.jwks_uri) if client_info.jwks_uri else None,
                    jwks=client_info.jwks,
                    software_id=client_info.software_id,
                    software_version=client_info.software_version,
                )
            )

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        pending_id = uuid.uuid4()
        async with self._sf() as session, session.begin():
            session.add(
                OAuthPendingAuth(
                    id=pending_id,
                    client_id=client.client_id,
                    redirect_uri=str(params.redirect_uri),
                    redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
                    scopes=list(params.scopes or []),
                    code_challenge=params.code_challenge,
                    state=params.state,
                    resource=params.resource,
                    expires_at=datetime.now(UTC) + PENDING_TTL,
                )
            )
        q = urlencode({"pending_id": str(pending_id)})
        return f"{self._settings.web_base_url.rstrip('/')}/settings/integrations/consent?{q}"

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        async with self._sf() as session:
            row = await session.get(OAuthAuthCode, hash_token(authorization_code))
            if row is None or row.consumed_at is not None:
                return None
            if row.client_id != client.client_id:
                return None
            if row.expires_at < datetime.now(UTC):
                return None
            return AuthorizationCode(
                code=authorization_code,
                scopes=list(row.scopes or []),
                expires_at=row.expires_at.timestamp(),
                client_id=row.client_id,
                code_challenge=row.code_challenge,
                redirect_uri=AnyUrl(row.redirect_uri),
                redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly,
                resource=row.resource,
                subject=subject_for(
                    user_id=row.user_id, workspace_id=row.workspace_id, profile_id=row.profile_id
                ),
            )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        access_raw = new_token("kaa")
        refresh_raw = new_token("kar")
        family = uuid.uuid4()
        now = datetime.now(UTC)
        async with self._sf() as session, session.begin():
            code_row = await session.get(OAuthAuthCode, hash_token(authorization_code.code))
            if code_row is None or code_row.consumed_at is not None:
                raise ValueError("invalid_grant")
            code_row.consumed_at = now
            user_id, workspace_id, profile_id = (
                code_row.user_id,
                code_row.workspace_id,
                code_row.profile_id,
            )
            await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
            session.add(
                OAuthTokenRow(
                    token_hash=hash_token(access_raw),
                    token_kind="access",
                    client_id=client.client_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    profile_id=profile_id,
                    scopes=list(authorization_code.scopes),
                    resource=authorization_code.resource,
                    refresh_family_id=family,
                    expires_at=now + ACCESS_TTL,
                )
            )
            session.add(
                OAuthTokenRow(
                    token_hash=hash_token(refresh_raw),
                    token_kind="refresh",
                    client_id=client.client_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    profile_id=profile_id,
                    scopes=list(authorization_code.scopes),
                    resource=authorization_code.resource,
                    refresh_family_id=family,
                    expires_at=now + REFRESH_TTL,
                )
            )
        return OAuthToken(
            access_token=access_raw,
            token_type="Bearer",
            expires_in=int(ACCESS_TTL.total_seconds()),
            refresh_token=refresh_raw,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        async with self._sf() as session:
            row = (
                await session.execute(
                    select(OAuthTokenRow).where(
                        OAuthTokenRow.token_hash == hash_token(refresh_token),
                        OAuthTokenRow.token_kind == "refresh",
                    )
                )
            ).scalar_one_or_none()
            if row is None or row.revoked_at is not None:
                return None
            if row.client_id != client.client_id:
                return None
            if row.expires_at and row.expires_at < datetime.now(UTC):
                return None
            return RefreshToken(
                token=refresh_token,
                client_id=row.client_id,
                scopes=list(row.scopes or []),
                expires_at=int(row.expires_at.timestamp()) if row.expires_at else None,
                resource=row.resource,
                subject=subject_for(
                    user_id=row.user_id, workspace_id=row.workspace_id, profile_id=row.profile_id
                ),
            )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        access_raw = new_token("kaa")
        new_refresh = new_token("kar")
        now = datetime.now(UTC)
        granted = scopes or list(refresh_token.scopes)
        async with self._sf() as session, session.begin():
            old = (
                await session.execute(
                    select(OAuthTokenRow).where(
                        OAuthTokenRow.token_hash == hash_token(refresh_token.token),
                        OAuthTokenRow.token_kind == "refresh",
                    )
                )
            ).scalar_one_or_none()
            if old is None or old.revoked_at is not None:
                raise ValueError("invalid_grant")
            old.revoked_at = now
            await set_request_context(
                session, user_id=str(old.user_id), workspace_id=str(old.workspace_id)
            )
            family = old.refresh_family_id or uuid.uuid4()
            session.add(
                OAuthTokenRow(
                    token_hash=hash_token(access_raw),
                    token_kind="access",
                    client_id=client.client_id,
                    user_id=old.user_id,
                    workspace_id=old.workspace_id,
                    profile_id=old.profile_id,
                    scopes=granted,
                    resource=refresh_token.resource or old.resource,
                    refresh_family_id=family,
                    expires_at=now + ACCESS_TTL,
                )
            )
            session.add(
                OAuthTokenRow(
                    token_hash=hash_token(new_refresh),
                    token_kind="refresh",
                    client_id=client.client_id,
                    user_id=old.user_id,
                    workspace_id=old.workspace_id,
                    profile_id=old.profile_id,
                    scopes=granted,
                    resource=refresh_token.resource or old.resource,
                    refresh_family_id=family,
                    expires_at=now + REFRESH_TTL,
                )
            )
        return OAuthToken(
            access_token=access_raw,
            token_type="Bearer",
            expires_in=int(ACCESS_TTL.total_seconds()),
            refresh_token=new_refresh,
            scope=" ".join(granted),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        async with self._sf() as session:
            row = (
                await session.execute(
                    select(OAuthTokenRow).where(
                        OAuthTokenRow.token_hash == hash_token(token),
                        OAuthTokenRow.token_kind.in_(("access", "pat")),
                    )
                )
            ).scalar_one_or_none()
            if row is None or row.revoked_at is not None:
                return None
            if row.expires_at and row.expires_at < datetime.now(UTC):
                return None
            # Touch last_used (best effort; separate short txn)
            await session.execute(
                update(OAuthTokenRow)
                .where(OAuthTokenRow.id == row.id)
                .values(last_used_at=datetime.now(UTC))
            )
            await session.commit()
            return AccessToken(
                token=token,
                client_id=row.client_id,
                scopes=list(row.scopes or []),
                expires_at=int(row.expires_at.timestamp()) if row.expires_at else None,
                resource=row.resource,
                subject=subject_for(
                    user_id=row.user_id, workspace_id=row.workspace_id, profile_id=row.profile_id
                ),
                claims={
                    "token_id": str(row.id),
                    "iss": self._settings.api_base_url.rstrip("/") + "/mcp",
                },
            )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        raw = token.token
        async with self._sf() as session, session.begin():
            row = (
                await session.execute(
                    select(OAuthTokenRow).where(OAuthTokenRow.token_hash == hash_token(raw))
                )
            ).scalar_one_or_none()
            if row is None:
                return
            now = datetime.now(UTC)
            row.revoked_at = now
            if row.refresh_family_id is not None:
                await session.execute(
                    update(OAuthTokenRow)
                    .where(
                        OAuthTokenRow.refresh_family_id == row.refresh_family_id,
                        OAuthTokenRow.revoked_at.is_(None),
                    )
                    .values(revoked_at=now)
                )


def _to_client_info(row: OAuthClient) -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=row.id,
        client_secret=None,
        client_id_issued_at=int(row.created_at.timestamp()) if row.created_at else int(time.time()),
        client_secret_expires_at=None,
        redirect_uris=[AnyUrl(u) for u in (row.redirect_uris or [])],
        grant_types=list(row.grant_types or ["authorization_code", "refresh_token"]),
        response_types=list(row.response_types or ["code"]),
        token_endpoint_auth_method=row.token_endpoint_auth_method or "none",
        scope=row.scope or " ".join(ALL_SCOPES),
        client_name=row.client_name or None,
        client_uri=AnyHttpUrl(row.client_uri) if row.client_uri else None,
        logo_uri=AnyHttpUrl(row.logo_uri) if row.logo_uri else None,
        contacts=list(row.contacts or []) or None,
        tos_uri=AnyHttpUrl(row.tos_uri) if row.tos_uri else None,
        policy_uri=AnyHttpUrl(row.policy_uri) if row.policy_uri else None,
        jwks_uri=AnyHttpUrl(row.jwks_uri) if row.jwks_uri else None,
        jwks=row.jwks,
        software_id=row.software_id,
        software_version=row.software_version,
    )


async def complete_consent(
    session: AsyncSession,
    *,
    pending_id: uuid.UUID,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    profile_id: uuid.UUID,
    scopes: list[str],
) -> str:
    """User approved consent: mint auth code and return redirect URL for the OAuth client."""
    pending = await session.get(OAuthPendingAuth, pending_id)
    if pending is None or pending.expires_at < datetime.now(UTC):
        raise ValueError("pending_expired")
    granted = [s for s in scopes if s in ALL_SCOPES] or list(pending.scopes or [])
    code = new_token("kac")
    session.add(
        OAuthAuthCode(
            code_hash=hash_token(code),
            client_id=pending.client_id,
            user_id=user_id,
            workspace_id=workspace_id,
            profile_id=profile_id,
            scopes=granted,
            code_challenge=pending.code_challenge,
            redirect_uri=pending.redirect_uri,
            redirect_uri_provided_explicitly=pending.redirect_uri_provided_explicitly,
            resource=pending.resource,
            expires_at=datetime.now(UTC) + CODE_TTL,
        )
    )
    await session.delete(pending)
    params: dict[str, Any] = {"code": code}
    if pending.state:
        params["state"] = pending.state
    return construct_redirect_uri(pending.redirect_uri, **params)
