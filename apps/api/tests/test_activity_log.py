import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DB_URL, TEST_OWNER_URL

INSERT = "INSERT INTO activity_log (id, actor_type, action) VALUES (gen_random_uuid(), :a, 'test.created')"


@pytest.fixture
async def owner_engine():
    e = create_async_engine(TEST_OWNER_URL)
    yield e
    await e.dispose()


@pytest.fixture
async def app_engine():
    e = create_async_engine(TEST_DB_URL)
    yield e
    await e.dispose()


# --- append-only triggers apply to everyone, including the table owner ---


async def test_owner_insert_allowed(owner_engine):
    async with owner_engine.begin() as conn:
        await conn.execute(text(INSERT), {"a": "system"})


@pytest.mark.parametrize(
    "sql", ["UPDATE activity_log SET action = 'x'", "DELETE FROM activity_log"]
)
async def test_owner_update_delete_rejected_by_trigger(owner_engine, sql):
    with pytest.raises(DBAPIError, match="append-only"):
        async with owner_engine.begin() as conn:
            await conn.execute(text(INSERT), {"a": "system"})
            await conn.execute(text(sql))


async def test_owner_truncate_rejected_by_trigger(owner_engine):
    with pytest.raises(DBAPIError, match="append-only"):
        async with owner_engine.begin() as conn:
            await conn.execute(text("TRUNCATE activity_log"))


async def test_invalid_actor_type_rejected(owner_engine):
    with pytest.raises(DBAPIError):
        async with owner_engine.begin() as conn:
            await conn.execute(text(INSERT), {"a": "robot"})


# --- the runtime role cannot even try ---


@pytest.mark.parametrize(
    "sql",
    ["UPDATE activity_log SET action = 'x'", "DELETE FROM activity_log", "TRUNCATE activity_log"],
)
async def test_app_role_has_no_update_delete_truncate_privilege(app_engine, sql):
    with pytest.raises(DBAPIError, match="permission denied"):
        async with app_engine.begin() as conn:
            await conn.execute(text(sql))


async def test_app_role_can_append_platform_rows_but_not_read_them(app_engine):
    async with app_engine.begin() as conn:
        await conn.execute(text(INSERT), {"a": "system"})  # workspace_id NULL: platform event
    async with app_engine.begin() as conn:
        n = (await conn.execute(text("SELECT count(*) FROM activity_log"))).scalar_one()
    assert n == 0  # tenants never see platform rows (no workspace set -> sees nothing)


# --- misc schema checks ---


async def test_extensions_installed(owner_engine):
    async with owner_engine.connect() as conn:
        names = {r[0] for r in await conn.execute(text("SELECT extname FROM pg_extension"))}
    assert {"vector", "pg_trgm", "citext", "pgcrypto"} <= names


async def test_database_is_at_head_revision(owner_engine):
    from alembic.script import ScriptDirectory

    from tests.conftest import _alembic_config

    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    async with owner_engine.connect() as conn:
        current = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
    assert current == head


async def test_app_role_is_not_superuser_and_cannot_bypass_rls(app_engine):
    async with app_engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            )
        ).one()
    assert tuple(row) == (False, False)
