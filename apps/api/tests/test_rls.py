"""Raw database-level isolation, as the RLS-restricted app role. No API involved."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.rls import set_request_context
from tests.conftest import TEST_DB_URL, Tenancy


@pytest.fixture
async def session(tenancy: Tenancy):
    # Depends on `tenancy` so this transaction closes BEFORE tenancy teardown drops rls_probe.
    engine = create_async_engine(TEST_DB_URL)
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine) as s, s.begin():
        yield s
    await engine.dispose()


async def _count(session, table: str) -> int:
    # table comes from a fixed test parametrization, never user input
    return (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()  # noqa: S608


@pytest.mark.parametrize("table", ["workspaces", "workspace_members", "rls_probe", "activity_log"])
async def test_no_context_sees_nothing(session, tenancy: Tenancy, table):
    assert await _count(session, table) == 0


async def test_empty_string_context_also_fails_closed(session, tenancy: Tenancy):
    await set_request_context(session, user_id="", workspace_id="")
    assert await _count(session, "rls_probe") == 0
    assert await _count(session, "workspace_members") == 0


async def test_user_sees_only_own_memberships_before_workspace_is_set(session, tenancy: Tenancy):
    await set_request_context(session, user_id=str(tenancy.users["a_member"]))
    rows = (
        await session.execute(text("SELECT workspace_id, user_id FROM workspace_members"))
    ).all()
    assert [(r[0], r[1]) for r in rows] == [(tenancy.ws_a, tenancy.users["a_member"])]
    assert await _count(session, "rls_probe") == 0  # no workspace chosen yet


async def test_workspace_context_shows_only_that_workspace(session, tenancy: Tenancy):
    await set_request_context(
        session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
    )
    labels = [r[0] for r in (await session.execute(text("SELECT label FROM rls_probe"))).all()]
    assert labels == ["a-row"]
    members = (
        await session.execute(text("SELECT DISTINCT workspace_id FROM workspace_members"))
    ).all()
    assert [m[0] for m in members] == [tenancy.ws_a]
    ws = (await session.execute(text("SELECT id FROM workspaces"))).all()
    assert [w[0] for w in ws] == [tenancy.ws_a]


async def test_cannot_insert_into_another_workspace(session, tenancy: Tenancy):
    await set_request_context(
        session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
    )
    with pytest.raises(DBAPIError, match="row-level security"):
        await session.execute(
            text("INSERT INTO rls_probe (workspace_id, label) VALUES (:w, 'evil')"),
            {"w": tenancy.ws_b},
        )


async def test_cannot_update_or_delete_other_workspace_rows(session, tenancy: Tenancy):
    await set_request_context(
        session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
    )
    upd = await session.execute(
        text("UPDATE rls_probe SET label = 'x' WHERE workspace_id = :w"), {"w": tenancy.ws_b}
    )
    dele = await session.execute(
        text("DELETE FROM rls_probe WHERE workspace_id = :w"), {"w": tenancy.ws_b}
    )
    assert upd.rowcount == 0 and dele.rowcount == 0  # type: ignore[attr-defined]


async def test_cannot_move_a_row_to_another_workspace(session, tenancy: Tenancy):
    await set_request_context(
        session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
    )
    with pytest.raises(DBAPIError, match="row-level security"):
        await session.execute(
            text("UPDATE rls_probe SET workspace_id = :w WHERE label = 'a-row'"),
            {"w": tenancy.ws_b},
        )


async def test_context_does_not_leak_across_transactions(tenancy: Tenancy):
    from sqlalchemy.ext.asyncio import AsyncSession

    engine = create_async_engine(TEST_DB_URL, pool_size=1, max_overflow=0)  # force connection reuse
    async with AsyncSession(engine) as s, s.begin():
        await set_request_context(
            s, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        assert await _count(s, "rls_probe") == 1
    async with AsyncSession(engine) as s, s.begin():
        assert await _count(s, "rls_probe") == 0  # same pooled connection, context must be gone
    await engine.dispose()


async def test_user_cannot_create_workspace_on_behalf_of_someone_else(session, tenancy: Tenancy):
    import uuid

    await set_request_context(session, user_id=str(tenancy.users["outsider"]), workspace_id="")
    with pytest.raises(DBAPIError, match="row-level security"):
        await session.execute(
            text("INSERT INTO workspaces (id, name, created_by) VALUES (:i, 'x', :o)"),
            {"i": uuid.uuid4(), "o": tenancy.users["a_owner"]},
        )
