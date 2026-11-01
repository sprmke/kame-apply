from httpx import AsyncClient


async def test_healthz(client: AsyncClient):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_readyz_checks_database(client: AsyncClient):
    r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


async def test_readyz_503_when_database_down():
    from httpx import ASGITransport
    from httpx import AsyncClient as C

    from app.core.config import Settings
    from app.main import create_app

    app = create_app(
        Settings(
            database_url="postgresql+asyncpg://nobody:nope@127.0.0.1:1/none",
            environment="test",
            log_json=False,
        )
    )
    async with app.router.lifespan_context(app):
        async with C(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/readyz")
    assert r.status_code == 503
    assert r.json() == {"status": "database_unavailable"}
