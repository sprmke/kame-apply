"""Setup apply: new mode, idempotency, stale rows, rollback, no network, revert, RBAC."""

from __future__ import annotations

import socket

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import Settings
from app.core.mail import Outbox
from app.main import create_app
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import Who, signup

S = "/api/v1/onboarding/setups"

RESUME = """ANA REYES
Customer Support Lead
Manila, Philippines
ana.reyes@example.com
https://linkedin.com/in/ana-reyes

Summary
Support lead with 6 years in SaaS onboarding and a track record of cutting response times.

Notice period: 30 days
Expected salary: PHP 60,000 per month

Skills: onboarding, Zendesk, team leadership, QA, SQL

Experience
2020 - 2025 Support Lead at Acme
Cut response times by 40 percent.

Education
2014 - 2018 BS Psychology, University of the Philippines
"""


@pytest.fixture
async def env_apply():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        app.state.mailer = Outbox()
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://a"
        ) as c:
            yield c, app


async def _draft(c, me: Who) -> dict:
    r = await c.post(S, json={"text": RESUME, "with_ai": False}, headers=me.h(me.personal))
    assert r.status_code == 202, r.text
    return r.json()


async def _apply(c, me: Who, draft_id: str, key: str, **body):
    return await c.post(
        f"{S}/{draft_id}/apply",
        json={"start_first_run": False, **body},
        headers={**me.h(me.personal), "Idempotency-Key": key},
    )


async def test_apply_writes_every_page_once(env_apply):
    c, _app = env_apply
    me = await signup(c)
    draft = await _draft(c, me)
    assert draft["status"] == "ready"

    patched = await c.patch(
        f"{S}/{draft['id']}/decisions",
        json={
            "items": {
                "profile.headline": {"action": "skip"},
                "answers.notice_period": {
                    "action": "add",
                    "edited": True,
                    "value": {"answer": "15 days", "approved": True},
                },
            },
            "seen_pages": [],
        },
        headers=me.h(me.personal),
    )
    assert patched.status_code == 200, patched.text

    dry = await c.post(f"{S}/{draft['id']}/validate", headers=me.h(me.personal))
    assert dry.status_code == 200
    assert dry.json() == {"ok": True, "errors": {}}

    r = await _apply(c, me, draft["id"], "key-1")
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["profile_id"]
    assert result["created"]["searches"]
    assert result["created"]["schedules"]
    assert result["created"]["resumes"]
    assert result["created"]["answers"]

    done = (await c.get(f"{S}/{draft['id']}", headers=me.h(me.personal))).json()
    assert done["status"] == "applied"

    profile = (
        await c.get(f"/api/v1/profiles/{result['profile_id']}", headers=me.h(me.personal))
    ).json()
    assert profile["display_name"] in {"Ana Reyes", "ANA REYES"}
    assert profile["headline"] in (None, "")  # skipped
    assert profile["location"] == "Manila, Philippines"
    assert profile["salary_prefs"]["floor"] == 60000
    assert profile["salary_prefs"]["currency"] == "PHP"
    assert profile["experiences"] == []  # rules mode reads basics, not work history
    assert any(skill["name"] == "Zendesk" for skill in profile["skills"])

    answers = (
        await c.get(f"/api/v1/profiles/{result['profile_id']}/answers", headers=me.h(me.personal))
    ).json()
    notice = next(row for row in answers if row["key"] == "notice_period")
    assert notice["answer"] == "15 days"
    assert notice["approved"] is True
    salary = next(row for row in answers if row["key"] == "salary_expectation")
    assert "60,000" in salary["answer"]

    tracks = (await c.get("/api/v1/tracks", headers=me.h(me.personal))).json()
    assert any(str(track["id"]) == str(result["created"]["searches"][0]) for track in tracks)

    again = await _apply(c, me, draft["id"], "key-1")
    assert again.status_code == 200
    assert again.json()["counts"] == result["counts"]

    different = await _apply(c, me, draft["id"], "key-2")
    assert different.status_code == 409
    assert different.json()["error"]["code"] == "setup_already_applied"


async def test_apply_requires_an_idempotency_key(env_apply):
    c, _app = env_apply
    me = await signup(c)
    draft = await _draft(c, me)
    r = await c.post(
        f"{S}/{draft['id']}/apply",
        json={"start_first_run": False},
        headers=me.h(me.personal),
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "idempotency_key_required"


async def test_stale_profile_blocks_apply_with_item_ids(env_apply):
    c, _app = env_apply
    me = await signup(c)
    draft = await _draft(c, me)
    profile_id = draft["profile_id"]
    await c.patch(
        f"/api/v1/profiles/{profile_id}",
        json={"headline": "Changed elsewhere"},
        headers=me.h(me.personal),
    )
    r = await _apply(c, me, draft["id"], "stale-key")
    assert r.status_code == 409
    error = r.json()["error"]
    assert error["code"] == "setup_stale"
    assert "profile.headline" in error["details"]["item_ids"]
    after = (await c.get(f"{S}/{draft['id']}", headers=me.h(me.personal))).json()
    assert after["status"] == "ready"


async def test_a_failure_rolls_back_the_whole_apply(env_apply, monkeypatch):
    c, _app = env_apply
    me = await signup(c)
    draft = await _draft(c, me)

    from app.onboarding import apply as apply_module

    async def boom(*_args, **_kwargs):
        raise RuntimeError("fault injected")

    monkeypatch.setattr(apply_module, "create_base", boom)
    r = await _apply(c, me, draft["id"], "fault-key")
    assert r.status_code == 500

    after = (await c.get(f"{S}/{draft['id']}", headers=me.h(me.personal))).json()
    assert after["status"] == "ready"
    profile = (
        await c.get(f"/api/v1/profiles/{draft['profile_id']}", headers=me.h(me.personal))
    ).json()
    assert profile["display_name"] == "My profile"
    assert profile["experiences"] == []


async def test_apply_makes_no_outbound_network_calls(env_apply, monkeypatch):
    c, _app = env_apply
    me = await signup(c)
    draft = await _draft(c, me)

    real_connect = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else ""
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError(f"outbound network during apply: {host}")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    r = await _apply(c, me, draft["id"], "offline-key")
    assert r.status_code == 200, r.text


async def test_revert_removes_untouched_rows_and_keeps_edits(env_apply):
    c, _app = env_apply
    me = await signup(c)
    draft = await _draft(c, me)
    r = await _apply(c, me, draft["id"], "revert-key")
    assert r.status_code == 200, r.text
    result = r.json()

    # Edit one created answer after apply; revert must keep it.
    notices = [
        row
        for row in (
            await c.get(
                f"/api/v1/profiles/{result['profile_id']}/answers", headers=me.h(me.personal)
            )
        ).json()
        if row["key"] == "notice_period"
    ]
    await c.patch(
        f"/api/v1/profiles/{result['profile_id']}/answers/{notices[0]['id']}",
        json={"answer": "Edited after setup"},
        headers=me.h(me.personal),
    )

    revert = await c.post(f"{S}/{draft['id']}/revert", headers=me.h(me.personal))
    assert revert.status_code == 200, revert.text
    body = revert.json()
    assert "searches" in body["removed"], body
    assert body["removed"]["searches"] >= 1
    assert any(item["kind"] == "answer" for item in body["kept"])

    tracks = (await c.get("/api/v1/tracks", headers=me.h(me.personal))).json()
    assert not any(str(track["id"]) == result["created"]["searches"][0] for track in tracks)
    answers = (
        await c.get(f"/api/v1/profiles/{result['profile_id']}/answers", headers=me.h(me.personal))
    ).json()
    assert any(row["answer"] == "Edited after setup" for row in answers)

    refused = await _apply(c, me, draft["id"], "revert-key")
    assert refused.status_code == 409


async def test_viewer_cannot_start_or_apply(env_apply):
    c, _app = env_apply
    owner = await signup(c)
    ws = (await c.post("/api/v1/workspaces", json={"name": "Team"}, headers=owner.h())).json()["id"]
    viewer = await signup(c)
    invite = await c.post(
        "/api/v1/workspace/invitations",
        json={"email": viewer.email, "role": "viewer"},
        headers=owner.h(ws),
    )
    assert invite.status_code == 201, invite.text
    token = invite.json().get("token")
    if not token:
        from tests.test_workspaces import last_token

        token = last_token(_app.state.mailer)
    accepted = await c.post("/api/v1/invitations/accept", json={"token": token}, headers=viewer.h())
    assert accepted.status_code == 200, accepted.text

    r = await c.post(S, json={"text": RESUME}, headers=viewer.h(ws))
    assert r.status_code == 403


async def _track_criteria(draft_id: str) -> list[dict]:
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.conftest import TEST_OWNER_URL

    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT t.name, c.structured FROM tracks t "
                    "JOIN track_criteria c ON c.track_id = t.id "
                    "JOIN setup_drafts d ON d.profile_id = t.profile_id "
                    "WHERE d.id = :id ORDER BY t.created_at"
                ),
                {"id": draft_id},
            )
        ).all()
    await engine.dispose()
    return [{"name": row[0], "structured": row[1]} for row in rows]


async def test_lowest_pay_fans_out_to_profile_answer_and_searches(env_apply):
    c, _app = env_apply
    me = await signup(c)
    draft = await _draft(c, me)
    patched = await c.patch(
        f"{S}/{draft['id']}/decisions",
        json={
            "items": {},
            "searches": {},
            "lowest_pay": {"amount": 45000, "currency": "php", "period": "month"},
            "lowest_pay_set": True,
            "seen_pages": [],
        },
        headers=me.h(me.personal),
    )
    assert patched.status_code == 200, patched.text

    r = await _apply(c, me, draft["id"], "pay-key")
    assert r.status_code == 200, r.text
    result = r.json()
    profile = (
        await c.get(f"/api/v1/profiles/{result['profile_id']}", headers=me.h(me.personal))
    ).json()
    assert profile["salary_prefs"] == {"floor": 45000.0, "currency": "PHP", "period": "month"}
    answers = (
        await c.get(f"/api/v1/profiles/{result['profile_id']}/answers", headers=me.h(me.personal))
    ).json()
    salary = next(row for row in answers if row["key"] == "salary_expectation")
    assert salary["answer"].startswith("PHP 45,000")
    assert salary["approved"] is True

    criteria = await _track_criteria(draft["id"])
    assert criteria
    for row in criteria:
        assert row["structured"]["salary"]["min"] == 45000.0
        assert row["structured"]["salary"]["currency"] == "PHP"


async def test_search_override_is_applied_with_guards(env_apply):
    c, _app = env_apply
    me = await signup(c)
    draft = await _draft(c, me)
    proposal = draft["bundle"]["searches"][0]
    edited = {
        **proposal,
        "name": "Edited support search",
        "criteria": {
            **proposal["criteria"],
            "titles": [{"title": "Support Operations Lead", "synonyms": [], "exclude": False}],
            "skills": {"must": ["Kubernetes"], "nice": ["Salesforce"], "exclude": []},
            "languages": ["de"],
            "education": "degree",
            "clearance": "secret",
        },
    }
    patched = await c.patch(
        f"{S}/{draft['id']}/decisions",
        json={
            "items": {},
            "searches": {proposal["variant"]: edited},
            "lowest_pay": None,
            "lowest_pay_set": False,
            "seen_pages": [],
        },
        headers=me.h(me.personal),
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["decisions"]["searches"], patched.json()["decisions"]

    r = await _apply(c, me, draft["id"], "edit-key")
    assert r.status_code == 200, r.text
    rows = await _track_criteria(draft["id"])
    edited_row = next(row for row in rows if row["name"] == "Edited support search")
    assert edited_row["structured"]["titles"][0]["title"] == "Support Operations Lead"
    assert edited_row["structured"]["skills"]["must"] == []  # not one of the person's skills
    assert edited_row["structured"]["languages"] == []
    assert edited_row["structured"]["education"] is None
    assert edited_row["structured"]["clearance"] is None
