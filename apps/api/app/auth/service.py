"""Auth business logic. Routers stay thin; every function runs in the request transaction.

`users` and the session/token tables are global (no workspace), so only this module and the
`current_user_id` dependency touch them.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.auth import tokens
from app.auth.models import AuthToken, OAuthIdentity, RefreshToken, User, UserSession
from app.auth.passwords import ahash_password, averify_password, needs_rehash
from app.core.config import Settings
from app.core.errors import AppError
from app.core.mail import Mail, Mailer

# Rolling refresh would otherwise keep a stolen but undetected session alive forever.
MAX_SESSION_AGE = timedelta(days=90)


class RefreshRace(Exception):
    """A just-rotated token was presented again: a multi-tab race, not theft. The router answers
    401 but must NOT clear the cookie, or it would erase the winning tab's fresh one."""


# A just-rotated token presented again within this window is a benign multi-tab race, not theft.
REFRESH_RACE_GRACE = timedelta(seconds=10)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Issued:
    user: User
    session_id: uuid.UUID
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class Meta:
    ip: str | None
    user_agent: str | None
    request_id: str | None


async def _start_session(db: AsyncSession, settings: Settings, user: User, meta: Meta) -> Issued:
    s = UserSession(user_id=user.id, ip=meta.ip, user_agent=(meta.user_agent or "")[:300] or None)
    db.add(s)
    await db.flush()
    return await _issue(db, settings, user, s.id)


async def _issue(db: AsyncSession, settings: Settings, user: User, session_id: uuid.UUID) -> Issued:
    raw, hashed = tokens.new_opaque_token()
    db.add(
        RefreshToken(
            session_id=session_id,
            token_hash=hashed,
            expires_at=_now() + timedelta(seconds=settings.refresh_token_ttl_seconds),
        )
    )
    access = tokens.issue_access_token(settings, user_id=user.id, session_id=session_id)
    return Issued(user, session_id, access, raw)


async def _send_token_mail(
    db: AsyncSession,
    settings: Settings,
    mailer: Mailer,
    user: User,
    *,
    kind: str,
    ttl_seconds: int,
) -> None:
    # One live token per kind: issuing a new one voids the older ones.
    await db.execute(
        update(AuthToken)
        .where(AuthToken.user_id == user.id, AuthToken.kind == kind, AuthToken.used_at.is_(None))
        .values(used_at=_now())
    )
    raw, hashed = tokens.new_opaque_token()
    db.add(
        AuthToken(
            user_id=user.id,
            kind=kind,
            token_hash=hashed,
            expires_at=_now() + timedelta(seconds=ttl_seconds),
        )
    )
    base = settings.web_base_url.rstrip("/")
    if kind == "email_verify":
        mail = Mail(
            user.email,
            "Verify your email",
            f"Confirm your email address:\n\n{base}/verify-email?token={raw}\n\n"
            "The link works once and expires in 48 hours.",
        )
    else:
        mail = Mail(
            user.email,
            "Reset your password",
            f"Choose a new password:\n\n{base}/reset-password?token={raw}\n\n"
            "The link works once and expires in 1 hour. If you did not ask for this, ignore it.",
        )
    await mailer.send(mail)


async def register(
    db: AsyncSession,
    settings: Settings,
    mailer: Mailer,
    *,
    email: str,
    password: str,
    name: str | None,
    meta: Meta,
) -> Issued:
    row = (
        await db.execute(
            pg_insert(User)
            .values(
                email=email.strip().lower(), password_hash=await ahash_password(password), name=name
            )
            .on_conflict_do_nothing(constraint="uq_users_email")
            .returning(User)
        )
    ).scalar_one_or_none()
    if row is None:
        raise AppError("email_taken", "An account with this email already exists", 409)
    user = row
    issued = await _start_session(db, settings, user, meta)
    from app.workspaces.service import create_workspace  # local: workspaces imports auth models

    await create_workspace(
        db, user_id=user.id, name="Personal", kind="personal", request_id=meta.request_id
    )
    await _send_token_mail(
        db,
        settings,
        mailer,
        user,
        kind="email_verify",
        ttl_seconds=settings.email_verify_ttl_seconds,
    )
    await audit.record_platform(
        db,
        action="auth.registered",
        actor_id=str(user.id),
        request_id=meta.request_id,
        target_type="user",
        target_id=str(user.id),
    )
    return issued


async def login(
    db: AsyncSession, settings: Settings, *, email: str, password: str, meta: Meta
) -> Issued:
    user = (
        await db.execute(select(User).where(User.email == email.strip().lower()))
    ).scalar_one_or_none()
    ok = await averify_password(user.password_hash if user else None, password)
    if not (user and ok and user.is_active):
        raise AppError("invalid_credentials", "Email or password is incorrect", 401)
    if needs_rehash(user.password_hash or ""):
        user.password_hash = await ahash_password(password)
    issued = await _start_session(db, settings, user, meta)
    await audit.record_platform(
        db,
        action="auth.login",
        actor_id=str(user.id),
        request_id=meta.request_id,
        target_type="session",
        target_id=str(issued.session_id),
    )
    return issued


async def refresh(
    db: AsyncSession, settings: Settings, *, raw: str | None, meta: Meta
) -> Issued | None:
    """Rotate the refresh token. Returns None for any failure so the router can answer 401 and
    still commit a reuse-triggered revocation (raising would roll it back)."""
    if not raw:
        return None
    rt = (
        await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == tokens.hash_token(raw))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if rt is None:
        return None
    session = (
        await db.execute(select(UserSession).where(UserSession.id == rt.session_id))
    ).scalar_one_or_none()
    if session is None:
        return None
    if session.revoked_at is not None or _now() - session.created_at > MAX_SESSION_AGE:
        return None
    if rt.used_at is not None:
        if _now() - rt.used_at < REFRESH_RACE_GRACE:
            raise RefreshRace
        # A rotated token came back: someone copied it. Kill the whole session.
        session.revoked_at = _now()
        await audit.record_platform(
            db,
            action="auth.refresh_reuse_detected",
            actor_id=str(session.user_id),
            request_id=meta.request_id,
            target_type="session",
            target_id=str(session.id),
        )
        return None
    if rt.expires_at <= _now():
        return None
    user = (await db.execute(select(User).where(User.id == session.user_id))).scalar_one()
    if not user.is_active:
        return None
    rt.used_at = _now()
    session.last_used_at = _now()
    return await _issue(db, settings, user, session.id)


async def logout(db: AsyncSession, session_id: uuid.UUID, meta: Meta) -> None:
    session = (
        await db.execute(select(UserSession).where(UserSession.id == session_id))
    ).scalar_one_or_none()
    await db.execute(
        update(UserSession)
        .where(UserSession.id == session_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    if session is not None:
        await audit.record_platform(
            db,
            action="auth.session_revoked",
            actor_id=str(session.user_id),
            request_id=meta.request_id,
            target_type="session",
            target_id=str(session_id),
        )


async def _consume(db: AsyncSession, raw: str, kind: str) -> AuthToken:
    t = (
        await db.execute(
            select(AuthToken)
            .where(AuthToken.token_hash == tokens.hash_token(raw), AuthToken.kind == kind)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if t is None or t.used_at is not None or t.expires_at <= _now():
        raise AppError("invalid_token", "This link is invalid or has expired", 400)
    t.used_at = _now()
    return t


async def verify_email(db: AsyncSession, *, raw: str, meta: Meta) -> None:
    t = await _consume(db, raw, "email_verify")
    await db.execute(
        update(User)
        .where(User.id == t.user_id, User.email_verified_at.is_(None))
        .values(email_verified_at=_now())
    )
    await audit.record_platform(
        db,
        action="auth.email_verified",
        actor_id=str(t.user_id),
        request_id=meta.request_id,
        target_type="user",
        target_id=str(t.user_id),
    )


async def resend_verification(
    db: AsyncSession, settings: Settings, mailer: Mailer, user: User
) -> None:
    if user.email_verified_at is None:
        await _send_token_mail(
            db,
            settings,
            mailer,
            user,
            kind="email_verify",
            ttl_seconds=settings.email_verify_ttl_seconds,
        )


async def forgot_password(
    db: AsyncSession, settings: Settings, mailer: Mailer, *, email: str
) -> None:
    """Always succeeds from the caller's view; mail goes out only if the account exists."""
    user = (
        await db.execute(select(User).where(User.email == email.strip().lower()))
    ).scalar_one_or_none()
    if user and user.is_active:
        await _send_token_mail(
            db,
            settings,
            mailer,
            user,
            kind="password_reset",
            ttl_seconds=settings.password_reset_ttl_seconds,
        )


async def reset_password(db: AsyncSession, *, raw: str, password: str, meta: Meta) -> None:
    t = await _consume(db, raw, "password_reset")
    await db.execute(
        update(User)
        .where(User.id == t.user_id)
        .values(
            password_hash=await ahash_password(password),
            # Receiving the mail proves ownership of the address.
            email_verified_at=func.coalesce(User.email_verified_at, func.now()),
        )
    )
    # A reset ends every signed-in device.
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == t.user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    await audit.record_platform(
        db,
        action="auth.password_reset",
        actor_id=str(t.user_id),
        request_id=meta.request_id,
        target_type="user",
        target_id=str(t.user_id),
    )


async def list_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[UserSession]:
    return list(
        (
            await db.execute(
                select(UserSession)
                .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
                .order_by(UserSession.last_used_at.desc())
            )
        ).scalars()
    )


async def revoke_session(
    db: AsyncSession, *, user_id: uuid.UUID, session_id: uuid.UUID, meta: Meta
) -> None:
    revoked = (
        await db.execute(
            update(UserSession)
            .where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=_now())
            .returning(UserSession.id)
        )
    ).first()
    if revoked is None:
        raise AppError("session_not_found", "Session not found", 404)
    await audit.record_platform(
        db,
        action="auth.session_revoked",
        actor_id=str(user_id),
        request_id=meta.request_id,
        target_type="session",
        target_id=str(session_id),
    )


class OAuthError(Exception):
    """Carries a stable code for the redirect back to the web app."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


async def oauth_sign_in(
    db: AsyncSession,
    settings: Settings,
    *,
    profile,
    link_user_id: uuid.UUID | None,
    meta: Meta,
) -> Issued | None:
    """Google callback logic. Returns a new session, or None when an existing user just linked.

    Never merges accounts silently: a Google email that matches a password account is refused
    until that user signs in and links Google from settings.
    """
    ident = (
        await db.execute(
            select(OAuthIdentity).where(
                OAuthIdentity.provider == "google", OAuthIdentity.subject == profile.subject
            )
        )
    ).scalar_one_or_none()

    if link_user_id is not None:
        owner = await db.get(User, link_user_id)
        # An unverified account may belong to someone squatting on another person's address. A
        # Google identity attached to it would survive the real owner's password reset.
        if owner is None or owner.email_verified_at is None:
            raise OAuthError("email_unverified")
        if ident is not None and ident.user_id != link_user_id:
            raise OAuthError("identity_in_use")
        if ident is None:
            db.add(OAuthIdentity(user_id=link_user_id, provider="google", subject=profile.subject))
            await audit.record_platform(
                db,
                action="auth.oauth_linked",
                actor_id=str(link_user_id),
                request_id=meta.request_id,
                after={"provider": "google"},
            )
        return None

    if ident is not None:
        user = (await db.execute(select(User).where(User.id == ident.user_id))).scalar_one()
        if not user.is_active:
            raise OAuthError("account_disabled")
        if user.email_verified_at is None:
            raise OAuthError("email_unverified")
        issued = await _start_session(db, settings, user, meta)
        await audit.record_platform(
            db,
            action="auth.login",
            actor_id=str(user.id),
            request_id=meta.request_id,
            target_type="session",
            target_id=str(issued.session_id),
            after={"via": "google"},
        )
        return issued

    if not profile.email_verified:
        raise OAuthError("email_not_verified")
    existing = (
        await db.execute(select(User.id).where(User.email == profile.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise OAuthError("account_exists")
    user = (
        await db.execute(
            pg_insert(User)
            .values(email=profile.email, name=profile.name, email_verified_at=_now())
            .on_conflict_do_nothing(constraint="uq_users_email")
            .returning(User)
        )
    ).scalar_one_or_none()
    if user is None:
        raise OAuthError("account_exists")
    db.add(OAuthIdentity(user_id=user.id, provider="google", subject=profile.subject))
    await db.flush()
    issued = await _start_session(db, settings, user, meta)
    from app.workspaces.service import create_workspace

    await create_workspace(
        db, user_id=user.id, name="Personal", kind="personal", request_id=meta.request_id
    )
    await audit.record_platform(
        db,
        action="auth.registered",
        actor_id=str(user.id),
        request_id=meta.request_id,
        target_type="user",
        target_id=str(user.id),
        after={"via": "google"},
    )
    return issued
