from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import health
from app.ai.providers import build_model
from app.api.v1.router import router as v1_router
from app.auth.google import GoogleOAuth
from app.core.config import Settings, get_settings
from app.core.db import create_engine, create_session_factory
from app.core.errors import ErrorEnvelope, install_error_handlers
from app.core.logging import configure_logging
from app.core.mail import Mailer
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from app.core.ratelimit import RateLimiter
from app.core.storage import build_storage


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    if settings.sentry_dsn:
        # PII stays out of error tracking (pii-guard.mdc): no default PII, no request bodies.
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            send_default_pii=False,
            include_local_variables=False,  # stack locals hold tokens, keys and password hashes
            max_request_body_size="never",
        )

    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    mcp_server = None
    mcp_asgi = None
    if settings.agent_bridge_enabled:
        from app.agent_bridge.mcp_app import build_mcp

        mcp_server, mcp_asgi = build_mcp(settings=settings, session_factory=session_factory)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = engine
        app.state.settings = settings
        app.state.mailer = getattr(app.state, "mailer", None) or Mailer(settings)
        app.state.rate_limiter = RateLimiter()
        app.state.google = getattr(app.state, "google", None) or GoogleOAuth(settings)
        app.state.model_factory = getattr(app.state, "model_factory", None) or build_model
        app.state.session_factory = session_factory
        storage = getattr(app.state, "storage", None) or build_storage(settings)
        app.state.storage = storage
        await storage.ensure_bucket()
        mcp_cm = None
        if mcp_server is not None:
            mcp_cm = mcp_server.session_manager.run()
            await mcp_cm.__aenter__()
        try:
            yield
        finally:
            if mcp_cm is not None:
                try:
                    await mcp_cm.__aexit__(None, None, None)
                except RuntimeError:
                    # ASGITransport may tear down lifespan on a different task than enter.
                    pass
            await engine.dispose()

    app = FastAPI(
        title="Kame Apply API",
        version="0.0.0",
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
        responses={"default": {"model": ErrorEnvelope}},
    )
    # Available before lifespan (rate-limit IP trust, CORS origins, etc.).
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(v1_router)
    if mcp_asgi is not None:
        app.mount("/mcp", mcp_asgi)
    return app


app = create_app()
