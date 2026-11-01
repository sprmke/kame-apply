import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.google import GoogleOAuth, new_pkce
from app.auth.models import OAuthIdentity, User
from app.auth.schemas import (
    AcceptedRead,
    AuthRead,
    ForgotIn,
    LoginIn,
    MeRead,
    MeUpdate,
    OAuthUrlRead,
    ProvidersRead,
    RegisterIn,
    ResetIn,
    SessionRead,
    TokenIn,
    UserRead,
)
from app.core.config import Settings
from app.core.errors import AppError, ErrorBody, ErrorEnvelope
from app.core.mail import Mailer
from app.core.ratelimit import client_ip
from app.core.security import Principal, current_principal, get_db

COOKIE = "kame_refresh"
COOKIE_PATH = "/api/v1/auth"

auth_router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(prefix="/me", tags=["me"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _mailer(request: Request) -> Mailer:
    return request.app.state.mailer


def _meta(request: Request) -> service.Meta:
    return service.Meta(
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
    )


def _limit(request: Request, key: str, limit: int, window: int) -> None:
    if _settings(request).auth_rate_limit_enabled:
        request.app.state.rate_limiter.check(key, limit=limit, window_seconds=window)


async def _load_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:  # session was live a moment ago; the user vanished mid-request
        raise AppError("unauthenticated", "Authentication required", 401)
    return user


def _user_read(u: User) -> UserRead:
    return UserRead(
        id=u.id,
        email=u.email,
        name=u.name,
        timezone=u.timezone,
        locale=u.locale,
        email_verified=u.email_verified_at is not None,
    )


def _set_cookie(response: Response, settings: Settings, raw: str) -> None:
    response.set_cookie(
        COOKIE,
        raw,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=COOKIE_PATH,
    )


def _clear_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        COOKIE, path=COOKIE_PATH, httponly=True, secure=settings.cookie_secure, samesite="lax"
    )


def _auth_response(issued: service.Issued, settings: Settings, response: Response) -> AuthRead:
    _set_cookie(response, settings, issued.refresh_token)
    return AuthRead(
        access_token=issued.access_token,
        expires_in=settings.access_token_ttl_seconds,
        user=_user_read(issued.user),
    )


@auth_router.post("/register", response_model=AuthRead, status_code=201)
async def register(
    body: RegisterIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    _limit(request, f"register:ip:{client_ip(request)}", 5, 3600)
    s = _settings(request)
    issued = await service.register(
        db,
        s,
        _mailer(request),
        email=body.email,
        password=body.password,
        name=body.name,
        meta=_meta(request),
    )
    return _auth_response(issued, s, response)


@auth_router.post("/login", response_model=AuthRead)
async def login(
    body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    # The tight cap is per (email, IP) so a stranger cannot lock a victim out from elsewhere; a
    # looser per-email cap still stops a distributed guess.
    _limit(request, f"login:ip:{client_ip(request)}", 20, 900)
    _limit(request, f"login:email-ip:{body.email.lower()}:{client_ip(request)}", 5, 900)
    _limit(request, f"login:email:{body.email.lower()}", 30, 900)
    s = _settings(request)
    issued = await service.login(
        db, s, email=body.email, password=body.password, meta=_meta(request)
    )
    return _auth_response(issued, s, response)


@auth_router.post("/refresh", response_model=AuthRead, responses={401: {"model": ErrorEnvelope}})
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _limit(request, f"refresh:ip:{client_ip(request)}", 60, 60)
    s = _settings(request)
    try:
        issued = await service.refresh(db, s, raw=request.cookies.get(COOKIE), meta=_meta(request))
    except service.RefreshRace:
        # Multi-tab race: reject, but leave the cookie alone (the winning tab just set a new one).
        body = ErrorEnvelope(
            error=ErrorBody(code="unauthenticated", message="Authentication required")
        )
        return JSONResponse(status_code=401, content=body.model_dump(mode="json"))
    if issued is None:
        # Returned, not raised, so a reuse-triggered revocation commits.
        body = ErrorEnvelope(
            error=ErrorBody(code="unauthenticated", message="Authentication required")
        )
        fail = JSONResponse(status_code=401, content=body.model_dump(mode="json"))
        _clear_cookie(fail, s)
        return fail
    return _auth_response(issued, s, response)


OAUTH_COOKIE = "kame_oauth"
OAUTH_COOKIE_PATH = "/api/v1/auth/google"


def _google(request: Request) -> GoogleOAuth:
    g: GoogleOAuth = request.app.state.google
    if not g.configured:
        raise AppError("oauth_not_configured", "Google sign-in is not set up", 404)
    return g


def _oauth_start(request: Request, g: GoogleOAuth, link_user_id: uuid.UUID | None):
    s = _settings(request)
    verifier, challenge = new_pkce()
    state = secrets.token_urlsafe(24)
    cookie = jwt.encode(
        {
            "typ": "oauth_state",
            "state": state,
            "verifier": verifier,
            "link": str(link_user_id) if link_user_id else None,
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        s.jwt_secret,
        algorithm="HS256",
    )
    return g.authorization_url(state=state, code_challenge=challenge), cookie


def _set_oauth_cookie(response: Response, s: Settings, value: str) -> None:
    response.set_cookie(
        OAUTH_COOKIE,
        value,
        max_age=600,
        httponly=True,
        secure=s.cookie_secure,
        samesite="lax",
        path=OAUTH_COOKIE_PATH,
    )


@auth_router.get("/google/start", include_in_schema=False)
async def google_start(request: Request):
    _limit(request, f"oauth:ip:{client_ip(request)}", 20, 3600)
    url, cookie = _oauth_start(request, _google(request), None)
    response = RedirectResponse(url, status_code=302)
    _set_oauth_cookie(response, _settings(request), cookie)
    return response


@auth_router.post("/google/link", response_model=OAuthUrlRead)
async def google_link(
    request: Request,
    response: Response,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    """Signed-in users link Google here; returns the Google URL for the browser to open."""
    user = await _load_user(db, principal.user_id)
    if user.email_verified_at is None:
        raise AppError("email_unverified", "Confirm your email first", 409)
    url, cookie = _oauth_start(request, _google(request), principal.user_id)
    _set_oauth_cookie(response, _settings(request), cookie)
    return OAuthUrlRead(url=url)


@auth_router.get("/google/callback", include_in_schema=False)
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    s = _settings(request)
    web = s.web_base_url.rstrip("/")

    def fail(code_: str) -> RedirectResponse:
        r = RedirectResponse(f"{web}/login?error={code_}", status_code=302)
        r.delete_cookie(OAUTH_COOKIE, path=OAUTH_COOKIE_PATH)
        return r

    g = _google(request)
    raw = request.cookies.get(OAUTH_COOKIE)
    if error or not code or not state or not raw:
        return fail("oauth_cancelled")
    try:
        claims = jwt.decode(raw, s.jwt_secret, algorithms=["HS256"], options={"require": ["exp"]})
    except jwt.PyJWTError:
        return fail("oauth_failed")
    if claims.get("typ") != "oauth_state" or not secrets.compare_digest(claims["state"], state):
        return fail("oauth_failed")
    try:
        profile = await g.fetch_profile(code=code, verifier=claims["verifier"])
    except Exception:
        return fail("oauth_failed")
    link = uuid.UUID(claims["link"]) if claims.get("link") else None
    try:
        issued = await service.oauth_sign_in(
            db, s, profile=profile, link_user_id=link, meta=_meta(request)
        )
    except service.OAuthError as e:
        return fail(e.code)
    if issued is None:
        r = RedirectResponse(f"{web}/settings/profile?linked=google", status_code=302)
    else:
        r = RedirectResponse(f"{web}/auth/callback", status_code=302)
        _set_cookie(r, s, issued.refresh_token)
    r.delete_cookie(OAUTH_COOKIE, path=OAUTH_COOKIE_PATH)
    return r


@auth_router.delete("/google/link", response_model=AcceptedRead)
async def google_unlink(
    request: Request,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, principal.user_id)
    if user.password_hash is None:
        # A Google-only account would lock itself out.
        raise AppError("last_sign_in_method", "Set a password before unlinking Google", 409)
    await db.execute(
        delete(OAuthIdentity).where(
            OAuthIdentity.user_id == principal.user_id, OAuthIdentity.provider == "google"
        )
    )
    from app.audit import service as audit

    await audit.record_platform(
        db,
        action="auth.oauth_unlinked",
        actor_id=str(principal.user_id),
        request_id=getattr(request.state, "request_id", None),
        after={"provider": "google"},
    )
    return AcceptedRead()


@auth_router.get("/providers", response_model=ProvidersRead)
async def auth_providers(request: Request):
    return ProvidersRead(google=request.app.state.google.configured)


@auth_router.post("/logout", response_model=AcceptedRead)
async def logout(
    request: Request,
    response: Response,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    await service.logout(db, principal.session_id, _meta(request))
    _clear_cookie(response, _settings(request))
    return AcceptedRead()


@auth_router.post("/verify-email", response_model=AcceptedRead)
async def verify_email(body: TokenIn, request: Request, db: AsyncSession = Depends(get_db)):
    _limit(request, f"verify:ip:{client_ip(request)}", 20, 3600)
    await service.verify_email(db, raw=body.token, meta=_meta(request))
    return AcceptedRead()


@auth_router.post("/verify-email/resend", response_model=AcceptedRead, status_code=202)
async def resend_verification(
    request: Request,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    _limit(request, f"resend:user:{principal.user_id}", 3, 3600)
    user = await _load_user(db, principal.user_id)
    await service.resend_verification(db, _settings(request), _mailer(request), user)
    return AcceptedRead()


@auth_router.post("/password/forgot", response_model=AcceptedRead, status_code=202)
async def forgot_password(body: ForgotIn, request: Request, db: AsyncSession = Depends(get_db)):
    _limit(request, f"forgot:ip:{client_ip(request)}", 5, 3600)
    _limit(request, f"forgot:email:{body.email.lower()}", 3, 3600)
    await service.forgot_password(db, _settings(request), _mailer(request), email=body.email)
    return AcceptedRead()


@auth_router.post("/password/reset", response_model=AcceptedRead)
async def reset_password(body: ResetIn, request: Request, db: AsyncSession = Depends(get_db)):
    _limit(request, f"reset:ip:{client_ip(request)}", 10, 3600)
    await service.reset_password(db, raw=body.token, password=body.password, meta=_meta(request))
    return AcceptedRead()


@me_router.get("", response_model=MeRead)
async def get_me(
    principal: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    user = await _load_user(db, principal.user_id)
    providers = list(
        (
            await db.execute(select(OAuthIdentity.provider).where(OAuthIdentity.user_id == user.id))
        ).scalars()
    )
    return MeRead(
        **_user_read(user).model_dump(),
        has_password=user.password_hash is not None,
        providers=providers,
    )


@me_router.patch("", response_model=UserRead)
async def update_me(
    body: MeUpdate,
    request: Request,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(db, principal.user_id)
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in changes.items():
        setattr(user, k, v)
    if changes:
        from app.audit import service as audit

        await audit.record_platform(
            db,
            action="user.updated",
            actor_id=str(user.id),
            request_id=getattr(request.state, "request_id", None),
            target_type="user",
            target_id=str(user.id),
            after={"fields": sorted(changes)},
        )
    return _user_read(user)


@me_router.get("/sessions", response_model=list[SessionRead])
async def list_sessions(
    principal: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    rows = await service.list_sessions(db, principal.user_id)
    return [
        SessionRead(
            id=r.id,
            user_agent=r.user_agent,
            ip=r.ip,
            created_at=r.created_at,
            last_used_at=r.last_used_at,
            current=r.id == principal.session_id,
        )
        for r in rows
    ]


@me_router.delete("/sessions/{session_id}", response_model=AcceptedRead)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    await service.revoke_session(
        db, user_id=principal.user_id, session_id=session_id, meta=_meta(request)
    )
    return AcceptedRead()
