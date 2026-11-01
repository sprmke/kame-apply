from httpx import AsyncClient


async def test_not_found_uses_error_envelope(client: AsyncClient):
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    body = r.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]


async def test_response_carries_request_id(client: AsyncClient):
    r = await client.get("/healthz")
    assert len(r.headers["x-request-id"]) >= 16


async def test_valid_incoming_request_id_is_kept(client: AsyncClient):
    r = await client.get("/healthz", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"


async def test_hostile_request_id_is_replaced(client: AsyncClient):
    r = await client.get("/healthz", headers={"X-Request-ID": "x" * 200})
    assert r.headers["x-request-id"] != "x" * 200


async def test_unhandled_error_is_generic_envelope():
    from httpx import ASGITransport
    from httpx import AsyncClient as C

    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings(environment="test", log_json=False))

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret internal detail")

    async with app.router.lifespan_context(app):
        async with C(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            r = await c.get("/boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "secret" not in r.text


async def test_validation_error_envelope():
    from fastapi import Query
    from httpx import ASGITransport
    from httpx import AsyncClient as C

    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings(environment="test", log_json=False))

    @app.get("/needs-int")
    async def needs_int(n: int = Query()):
        return {"n": n}

    async with app.router.lifespan_context(app):
        async with C(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/needs-int?n=abc")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert r.json()["error"]["details"][0]["loc"] == ["query", "n"]
