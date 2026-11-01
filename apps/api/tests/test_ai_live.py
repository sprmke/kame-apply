"""Real provider calls. Skipped unless RUN_LIVE_AI=1; keys come from apps/api/.env (gitignored).

RUN_LIVE_AI=1 uv run pytest apps/api/tests/test_ai_live.py -q
"""

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_AI") != "1", reason="live AI tests are opt-in"
)


def _dotenv() -> dict[str, str]:
    out = {}
    for line in (Path(__file__).resolve().parents[1] / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


@pytest.fixture
async def client():
    app = create_app(
        Settings(
            database_url=TEST_DB_URL,
            environment="test",
            log_json=False,
            auth_rate_limit_enabled=False,
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t", timeout=90
        ) as c:
            yield c


@pytest.mark.parametrize(
    "provider,env_key", [("gemini", "GEMINI_API_KEYS"), ("groq", "GROQ_API_KEY")]
)
async def test_real_key_validates_and_is_metered(client, provider, env_key):
    key = _dotenv()[env_key].split(",")[0]
    me = await signup(client)
    ws = me.personal
    r = await client.post(
        "/api/v1/ai/credentials", json={"provider": provider, "api_key": key}, headers=me.h(ws)
    )
    assert r.status_code == 201
    cid = r.json()["id"]
    t = await client.post(f"/api/v1/ai/credentials/{cid}/test", headers=me.h(ws))
    assert t.json() == {"status": "valid", "detail": None}, t.text
    usage = (await client.get("/api/v1/ai/usage", headers=me.h(ws))).json()
    assert usage["by_feature"][0]["feature"] == "credential_test"

    bad = await client.post(
        "/api/v1/ai/credentials",
        json={"provider": provider, "api_key": "not-a-real-key-123"},
        headers=me.h(ws),
    )
    t = await client.post(f"/api/v1/ai/credentials/{bad.json()['id']}/test", headers=me.h(ws))
    assert t.json()["status"] == "invalid", t.text
