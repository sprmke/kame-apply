import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

# Runtime (RLS-restricted) role for the app under test; owner role only for migrations/setup.
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://kame_apply_app:kame_apply_app_local_only@127.0.0.1:5442/kame_apply_test",
)
TEST_OWNER_URL = os.environ.get(
    "TEST_OWNER_DATABASE_URL",
    "postgresql+asyncpg://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply_test",
)
# Must be set before app modules read settings.
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["MIGRATION_DATABASE_URL"] = TEST_OWNER_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_JSON"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def _alembic_config() -> Config:
    api_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(api_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(api_root / "migrations"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_db() -> None:
    """Fresh schema for the session: downgrade to base, upgrade to head."""
    cfg = _alembic_config()
    # A crashed earlier run can leave the probe table behind; it would block the downgrade.
    import asyncio

    from sqlalchemy import text as _text
    from sqlalchemy.ext.asyncio import create_async_engine as _engine

    async def _drop_probe() -> None:
        e = _engine(TEST_OWNER_URL)
        async with e.begin() as conn:
            await conn.execute(_text("DROP TABLE IF EXISTS rls_probe"))
        await e.dispose()

    asyncio.run(_drop_probe())
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app(Settings(database_url=TEST_DB_URL, environment="test", log_json=False))
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


# ---------------------------------------------------------------------------
# Tenancy fixtures: two workspaces with users in every role, plus an RLS probe table.
# Seeding runs as the OWNER role (bypasses RLS); everything under test uses the app role.
# ---------------------------------------------------------------------------
import uuid  # noqa: E402
from dataclasses import dataclass  # noqa: E402

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.rls import tenant_rls_sql  # noqa: E402


@dataclass(frozen=True)
class Tenancy:
    ws_a: uuid.UUID
    ws_b: uuid.UUID
    users: dict[
        str, uuid.UUID
    ]  # keys: a_owner a_admin a_member a_viewer b_owner outsider a_inactive


@pytest.fixture
async def tenancy() -> AsyncIterator[Tenancy]:
    engine = create_async_engine(TEST_OWNER_URL)
    ws_a, ws_b = uuid.uuid4(), uuid.uuid4()
    names = ["a_owner", "a_admin", "a_member", "a_viewer", "a_inactive", "b_owner", "outsider"]
    users = {n: uuid.uuid4() for n in names}
    async with engine.begin() as conn:
        for n, uid in users.items():
            await conn.execute(
                text("INSERT INTO users (id, email) VALUES (:id, :e)"),
                {"id": uid, "e": f"{n}-{uid.hex[:8]}@example.test"},
            )
        for wid, owner in ((ws_a, users["a_owner"]), (ws_b, users["b_owner"])):
            await conn.execute(
                text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'ws', :o)"),
                {"id": wid, "o": owner},
            )
        members = [
            (ws_a, "a_owner", "owner", True),
            (ws_a, "a_admin", "admin", True),
            (ws_a, "a_member", "member", True),
            (ws_a, "a_viewer", "viewer", True),
            (ws_a, "a_inactive", "member", False),
            (ws_b, "b_owner", "owner", True),
        ]
        for wid, n, role, active in members:
            await conn.execute(
                text(
                    "INSERT INTO workspace_members (workspace_id, user_id, role, is_active) "
                    "VALUES (:w, :u, :r, :a)"
                ),
                {"w": wid, "u": users[n], "r": role, "a": active},
            )
        await conn.execute(text("DROP TABLE IF EXISTS rls_probe"))
        await conn.execute(
            text(
                "CREATE TABLE rls_probe (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), "
                "workspace_id uuid NOT NULL REFERENCES workspaces(id), label text NOT NULL)"
            )
        )
        for stmt in tenant_rls_sql("rls_probe"):
            await conn.execute(text(stmt))
        await conn.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON rls_probe TO kame_apply_app")
        )
        for wid, label in ((ws_a, "a-row"), (ws_b, "b-row")):
            await conn.execute(
                text("INSERT INTO rls_probe (workspace_id, label) VALUES (:w, :l)"),
                {"w": wid, "l": label},
            )
    yield Tenancy(ws_a=ws_a, ws_b=ws_b, users=users)
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS rls_probe"))
        await conn.execute(
            text("DELETE FROM workspace_members WHERE workspace_id = ANY(:w)"), {"w": [ws_a, ws_b]}
        )
        await conn.execute(text("DELETE FROM workspaces WHERE id = ANY(:w)"), {"w": [ws_a, ws_b]})
        await conn.execute(
            text("DELETE FROM users WHERE id = ANY(:u)"), {"u": list(users.values())}
        )
    await engine.dispose()
