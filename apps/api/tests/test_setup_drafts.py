"""Setup drafts: RLS, the one-open-draft rule, retention, bundle contracts, target validation."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.rls import set_request_context
from app.onboarding import schemas as s
from app.onboarding.setup_service import clear_setup_content, expire_setups
from app.onboarding.targets import TargetError, validate_target
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL, Tenancy


async def _profile(engine, workspace_id: uuid.UUID, name: str) -> uuid.UUID:
    pid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO candidate_profiles (id, workspace_id, display_name, minimization) "
                "VALUES (:id, :w, :n, '{}'::jsonb)"
            ),
            {"id": pid, "w": workspace_id, "n": name},
        )
    return pid


async def _insert_draft(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    profile_id: uuid.UUID,
    status: str = "ready",
    expires_at: datetime | None = None,
    bundle: dict | None = None,
    decisions: dict | None = None,
) -> uuid.UUID:
    draft_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO setup_drafts "
            "(id, workspace_id, profile_id, status, expires_at, bundle, decisions) "
            "VALUES (:id, :w, :p, :s, :e, CAST(:b AS jsonb), CAST(:d AS jsonb))"
        ),
        {
            "id": draft_id,
            "w": workspace_id,
            "p": profile_id,
            "s": status,
            "e": expires_at,
            "b": None if bundle is None else json.dumps(bundle),
            "d": json.dumps(decisions or {}),
        },
    )
    return draft_id


@pytest.fixture
async def setup_env(tenancy: Tenancy):
    engine = create_async_engine(TEST_DB_URL)
    owner = create_async_engine(TEST_OWNER_URL)
    profile_a = await _profile(owner, tenancy.ws_a, "Ana")
    profile_b = await _profile(owner, tenancy.ws_b, "Bea")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield {
        "tenancy": tenancy,
        "factory": factory,
        "profile_a": profile_a,
        "profile_b": profile_b,
    }
    async with owner.begin() as conn:
        await conn.execute(
            text("DELETE FROM candidate_profiles WHERE id = ANY(:p)"),
            {"p": [profile_a, profile_b]},
        )
    await engine.dispose()
    await owner.dispose()


async def test_rows_are_visible_only_in_their_workspace(setup_env, tenancy: Tenancy):
    factory = setup_env["factory"]
    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        await _insert_draft(session, workspace_id=tenancy.ws_a, profile_id=setup_env["profile_a"])
    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["b_owner"]), workspace_id=str(tenancy.ws_b)
        )
        await _insert_draft(session, workspace_id=tenancy.ws_b, profile_id=setup_env["profile_b"])

    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        rows = (await session.execute(text("SELECT profile_id FROM setup_drafts"))).scalars().all()
        assert rows == [setup_env["profile_a"]]

    async with factory() as session:
        assert (await session.execute(text("SELECT count(*) FROM setup_drafts"))).scalar_one() == 0


async def test_another_workspace_cannot_be_written(setup_env, tenancy: Tenancy):
    factory = setup_env["factory"]
    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        with pytest.raises(Exception, match="row-level security"):
            await _insert_draft(
                session, workspace_id=tenancy.ws_b, profile_id=setup_env["profile_b"]
            )


async def test_one_open_draft_per_profile(setup_env, tenancy: Tenancy):
    factory = setup_env["factory"]
    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        await _insert_draft(
            session, workspace_id=tenancy.ws_a, profile_id=setup_env["profile_a"], status="ready"
        )
    with pytest.raises(IntegrityError):
        async with factory() as session, session.begin():
            await set_request_context(
                session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
            )
            await _insert_draft(
                session,
                workspace_id=tenancy.ws_a,
                profile_id=setup_env["profile_a"],
                status="queued",
            )

    # A finished draft does not block a new one.
    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        rows = (await session.execute(text("SELECT id FROM setup_drafts"))).scalars().all()
        await session.execute(
            text("UPDATE setup_drafts SET status = 'applied' WHERE id = ANY(:i)"), {"i": rows}
        )
        await _insert_draft(
            session, workspace_id=tenancy.ws_a, profile_id=setup_env["profile_a"], status="ready"
        )


async def test_expire_setups_closes_old_open_drafts(setup_env, tenancy: Tenancy):
    factory = setup_env["factory"]
    now = datetime.now(UTC)
    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        old = await _insert_draft(
            session,
            workspace_id=tenancy.ws_a,
            profile_id=setup_env["profile_a"],
            expires_at=now - timedelta(days=1),
        )

    assert await expire_setups(factory, now=now) >= 1

    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        status = (
            await session.execute(text("SELECT status FROM setup_drafts WHERE id = :i"), {"i": old})
        ).scalar_one()
        assert status == "expired"


async def test_clear_setup_content_keeps_the_metadata_row(setup_env, tenancy: Tenancy):
    factory = setup_env["factory"]
    now = datetime.now(UTC)
    bundle = {"schema_version": 1, "items": [], "searches": [], "notices": [], "counts": {}}
    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        draft_id = await _insert_draft(
            session,
            workspace_id=tenancy.ws_a,
            profile_id=setup_env["profile_a"],
            status="applied",
            bundle=bundle,
            decisions={"items": {"profile.headline": {"action": "add"}}},
        )
        await session.execute(
            text("UPDATE setup_drafts SET steps = CAST(:s AS jsonb) WHERE id = :i"),
            {
                "s": '{"stated_signals": {"status": "done", "signals": [{"value": "x"}]}, '
                '"normalize": {"status": "done", "country": "PH"}}',
                "i": draft_id,
            },
        )
        await session.execute(
            text("UPDATE setup_drafts SET updated_at = :t WHERE id = :i"),
            {"t": now - timedelta(days=31), "i": draft_id},
        )

    assert await clear_setup_content(factory, now=now) >= 1

    async with factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(tenancy.users["a_owner"]), workspace_id=str(tenancy.ws_a)
        )
        row = (
            await session.execute(
                text("SELECT bundle, decisions, steps FROM setup_drafts WHERE id = :i"),
                {"i": draft_id},
            )
        ).one()
        assert row[0] is None
        assert row[1] == {}
        assert "signals" not in row[2]["stated_signals"]
        assert "country" not in row[2]["normalize"]
        assert row[2]["stated_signals"]["status"] == "done"


def test_needs_you_item_cannot_carry_a_value():
    with pytest.raises(ValidationError):
        s.SetupItem(
            id="answers.work_authorization.PH",
            group="answers",
            target="answers.work_authorization.PH",
            kind="value",
            value={"answer": "US citizen", "approved": True},
            source="resume",
            reason_key="setup.reason.stated",
            needs_you=True,
        )


def test_bundle_rejects_duplicate_item_ids():
    item: dict[str, Any] = dict(
        group="answers",
        target="answers.notice_period",
        kind="value",
        value={"answer": "30 days", "approved": True},
        source="resume",
        reason_key="setup.reason.stated",
    )
    with pytest.raises(ValidationError):
        s.SetupBundle(
            items=[
                s.SetupItem(id="answers.notice_period", **item),
                s.SetupItem(id="answers.notice_period", **item),
            ]
        )


def test_decisions_reject_unknown_actions():
    with pytest.raises(ValidationError):
        s.SetupDecisions.model_validate({"items": {"profile.headline": {"action": "delete"}}})


def test_setup_create_needs_exactly_one_source():
    with pytest.raises(ValidationError):
        s.SetupCreate()
    with pytest.raises(ValidationError):
        s.SetupCreate(document_id=uuid.uuid4(), text="x" * 200)
    assert s.SetupCreate(text="x" * 200).text


@pytest.mark.parametrize(
    ("target", "value"),
    [
        ("profile.display_name", "Ana Reyes"),
        ("profile.headline", "Frontend engineer"),
        ("profile.timezone", "Asia/Manila"),
        ("profile.links", [{"label": "LinkedIn", "url": "https://linkedin.com/in/ana"}]),
        (
            "profile.experience",
            {"company": "Acme", "title": "Engineer", "start_date": "2021-01-01"},
        ),
        ("profile.skill", {"name": "js"}),
        ("answers.notice_period", {"answer": "30 days", "approved": True}),
        (
            "answers.work_authorization.PH",
            {"answer": "Filipino citizen", "approved": True},
        ),
        ("writing.preset", "plain"),
        ("studio.base_resume", {"label": "Frontend engineer", "page_size": "a4"}),
        ("account.name", "Ana Reyes"),
        ("account.timezone", "Asia/Manila"),
        ("industry.field", "technology"),
    ],
)
def test_targets_accept_valid_values(target, value):
    assert validate_target(target, value) is not None


@pytest.mark.parametrize(
    ("target", "value"),
    [
        ("profile.display_name", ""),
        ("profile.headline", "x" * 400),
        ("profile.link", "https://example.com"),
        ("profile.experience", {"company": "Acme"}),
        ("answers.notice_period", {"answer": "30 days", "approved": "yes"}),
        ("answers.work_authorization", {"answer": "Citizen", "approved": True}),
        ("writing.preset", "poetic"),
        ("studio.base_resume", {"label": "x", "page_size": "legal"}),
        ("account.timezone", "Mars/Olympus"),
        ("industry.field", ""),
    ],
)
def test_targets_reject_invalid_values(target, value):
    with pytest.raises(TargetError):
        validate_target(target, value)
