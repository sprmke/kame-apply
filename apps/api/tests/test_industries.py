"""Industry packs, workspace fields, the experience manifest, and track defaults."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.industries.registry import get_pack, list_packs, pack_for_template, require_pack
from app.industries.resolve import resolve_pack, resolve_workspace
from app.industries.schema import CRITERIA_FIELDS
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_ai import env  # noqa: F401
from tests.test_tracks import _criteria, _profile, seeded_templates  # noqa: F401
from tests.test_workspaces import env as ws_env  # noqa: F401
from tests.test_workspaces import signup, team_with

IND = "/api/v1/industries"
W = "/api/v1/workspace"
T = "/api/v1/tracks"


# --- pack registry and resolver (no DB) --------------------------------------------------------


def test_every_pack_has_a_state_for_every_criteria_field():
    for pack in list_packs():
        manifest = resolve_pack(pack)
        assert set(manifest["states"]) == CRITERIA_FIELDS, pack.key
        listed = [field for group in manifest["groups"] for field in group["fields"]]
        assert sorted(listed) == sorted(CRITERIA_FIELDS), pack.key


def test_technology_manifest_pins_todays_behavior():
    pack = get_pack("technology")
    assert pack is not None
    manifest = resolve_pack(pack)
    assert manifest["states"]["shifts"] == "hidden"
    assert manifest["states"]["salary_includes"] == "hidden"
    assert manifest["states"]["facets"] == "hidden"
    assert manifest["states"]["remote_eligibility"] == "visible"
    assert manifest["labels"]["skills"] == "criteria.skills.tech_stack"
    assert manifest["features"]["github_links"] is True
    assert manifest["features"]["coding_practice"] is True
    weights = pack.matching.weights
    assert weights["skills"] == 0.28 and weights["location"] == 0.10
    assert "portfolio project" in " ".join(pack.profile.gap_actions)


def test_general_is_the_base_layer_and_the_union_keeps_the_most_visible_state():
    general = require_pack("general")
    assert resolve_pack(general)["states"]["shifts"] == "collapsed"
    union = resolve_workspace([general, require_pack("technology")], primary_key="technology")
    # Technology hides shifts, General collapses them, so a two-field workspace keeps them one
    # tap away instead of removing a control the person may still need.
    assert union["states"]["shifts"] == "collapsed"
    assert union["label_key"] == "industry.technology.label"
    assert union["profile_sections"]


def test_hospitality_manifest_is_kitchen_first():
    manifest = resolve_pack(require_pack("hospitality"))
    assert manifest["states"]["shifts"] == "visible"
    assert manifest["states"]["facets"] == "visible"
    assert manifest["states"]["remote_eligibility"] == "hidden"
    assert manifest["states"]["education"] == "hidden"
    assert manifest["labels"]["skills"] == "criteria.skills.techniques"
    groups = {group["key"]: group["fields"] for group in manifest["groups"]}
    assert groups["kitchen"] == ["facets"]
    assert "shifts" in groups["when"]
    assert manifest["features"]["github_links"] is False
    assert {facet["key"] for facet in manifest["facets"]} == {
        "cuisine",
        "kitchen_type",
        "station",
        "covers_band",
    }


def test_every_pack_label_key_exists_in_english_catalog():
    root = Path(__file__).resolve().parents[3]
    catalog = json.loads((root / "apps/web/i18n/locales/en.json").read_text())

    def lookup(key: str) -> object:
        value: object = catalog
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    for pack in list_packs():
        keys = [pack.label_key]
        keys += [family.label_key for family in pack.role_families]
        keys += [facet.label_key for facet in pack.facets]
        keys += [option.label_key for facet in pack.facets for option in facet.options]
        keys += [credential.label_key for credential in pack.credentials]
        keys += [step.label_key for step in pack.seniority_ladder]
        keys += list(pack.ui.labels.values())
        keys += list(pack.profile.labels.values())
        for key in keys:
            assert isinstance(lookup(key), str), f"{pack.key}: missing i18n key {key}"


def test_template_industries_map_to_available_packs():
    assert pack_for_template("technology") == "technology"
    assert pack_for_template("hospitality") == "hospitality"
    assert pack_for_template("healthcare") == "healthcare"
    assert pack_for_template("legal") == "general"
    assert pack_for_template(None) == "technology"


# --- API ---------------------------------------------------------------------------------------


async def test_industries_list_and_workspace_experience(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)

    listed = await c.get(IND, headers=h)
    assert listed.status_code == 200, listed.text
    assert {"general", "technology", "hospitality"} <= {
        item["key"] for item in listed.json()["items"]
    }
    tech = next(item for item in listed.json()["items"] if item["key"] == "technology")
    assert tech["role_families"]

    fields = await c.get(W + "/industries", headers=h)
    assert fields.status_code == 200, fields.text
    items = fields.json()["items"]
    assert [item["key"] for item in items] == ["technology", "general"]
    assert items[0]["is_primary"] is True

    experience = await c.get(W + "/experience", headers=h)
    assert experience.status_code == 200, experience.text
    body = experience.json()
    assert body["primary"] == "technology"
    assert body["manifest"]["states"]["shifts"] == "hidden"
    assert set(body["packs"]) == {"technology", "general"}

    by_path = await c.get(f"/api/v1/workspaces/{me.personal}/experience", headers=h)
    assert by_path.status_code == 200
    assert by_path.json()["primary"] == "technology"
    ghost = await c.get(f"/api/v1/workspaces/{uuid.uuid4()}/experience", headers=h)
    assert ghost.status_code == 404


async def test_members_cannot_change_fields_and_viewers_can_read(ws_env):  # noqa: F811
    c, outbox = ws_env
    owner = await signup(c)
    ws, people = await team_with(c, owner, outbox, {"ad": "admin", "m": "member", "v": "viewer"})

    assert (await c.get(W + "/industries", headers=people["v"].h(ws))).status_code == 200
    for actor in (people["m"], people["v"]):
        r = await c.post(W + "/industries", json={"key": "hospitality"}, headers=actor.h(ws))
        assert r.status_code == 403
    admin = await c.post(W + "/industries", json={"key": "hospitality"}, headers=people["ad"].h(ws))
    assert admin.status_code == 200, admin.text
    assert [item["key"] for item in admin.json()["items"]] == [
        "technology",
        "hospitality",
        "general",
    ]
    general = await c.post(W + "/industries", json={"key": "general"}, headers=owner.h(ws))
    assert general.status_code == 422


async def test_removing_the_primary_field_moves_tracks_and_falls_back(env, seeded_templates):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)
    created = await c.post(
        T, json={"profile_id": p["id"], "name": "Tech roles", "criteria": _criteria()}, headers=h
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]
    assert created.json()["industry"] == "technology"

    removed = await c.delete(W + "/industries/technology", headers=h)
    assert removed.status_code == 200, removed.text
    assert [item["key"] for item in removed.json()["items"]] == ["general"]

    detail = await c.get(T + f"/{tid}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["industry"] == "general"
    experience = await c.get(W + "/experience", headers=h)
    assert experience.json()["primary"] == "general"

    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.connect() as conn:
        actions = {
            row[0]
            for row in (
                await conn.execute(
                    text(
                        "SELECT action FROM activity_log WHERE workspace_id = :w "
                        "AND action IN ('workspace.industry_removed', 'track.industry_changed')"
                    ),
                    {"w": uuid.UUID(me.personal)},
                )
            ).all()
        }
    await engine.dispose()
    assert actions == {"workspace.industry_removed", "track.industry_changed"}


async def test_chef_template_uses_the_hospitality_pack(env, seeded_templates):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)
    added = await c.post(W + "/industries", json={"key": "hospitality"}, headers=h)
    assert added.status_code == 200, added.text
    created = await c.post(T, json={"profile_id": p["id"], "template_slug": "chef"}, headers=h)
    assert created.status_code == 201, created.text
    assert created.json()["industry"] == "hospitality"


async def test_track_industry_must_be_enabled_and_facets_must_exist(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)
    created = await c.post(
        T, json={"profile_id": p["id"], "name": "Tech", "criteria": _criteria()}, headers=h
    )
    tid = created.json()["id"]

    bad = await c.patch(T + f"/{tid}", json={"industry": "hospitality"}, headers=h)
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "unknown_industry"

    ok = await c.patch(T + f"/{tid}", json={"industry": "general"}, headers=h)
    assert ok.status_code == 200 and ok.json()["industry"] == "general"

    facets = await c.put(
        T + f"/{tid}/criteria",
        json={"criteria": {**_criteria(), "facets": {"cuisine": ["filipino"]}}},
        headers=h,
    )
    assert facets.status_code == 422
    assert facets.json()["error"]["code"] == "unknown_facet"


async def test_hospitality_track_accepts_kitchen_facets(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)
    added = await c.post(W + "/industries", json={"key": "hospitality"}, headers=h)
    assert added.status_code == 200, added.text

    body = {
        "profile_id": p["id"],
        "name": "Sous chef Dubai",
        "industry": "hospitality",
        "criteria": {
            **_criteria(titles=[{"title": "Sous chef", "synonyms": [], "exclude": False}]),
            "shifts": ["evening", "weekend"],
            "facets": {
                "cuisine": ["filipino", "japanese"],
                "kitchen_type": ["hotel"],
                "station": ["grill", "sauce"],
                "covers_band": ["band_150_300"],
            },
            "salary": {
                "min": 6000,
                "currency": "AED",
                "period": "month",
                "includes": ["accommodation", "meals"],
            },
        },
    }
    created = await c.post(T, json=body, headers=h)
    assert created.status_code == 201, created.text
    detail = created.json()
    assert detail["industry"] == "hospitality"
    stored = detail["criteria"]["structured"]
    assert stored["shifts"] == ["evening", "weekend"]
    assert stored["salary"]["includes"] == ["accommodation", "meals"]
    assert stored["facets"]["cuisine"] == ["filipino", "japanese"]

    bad = await c.post(
        T,
        json={
            **body,
            "name": "Bad facet",
            "criteria": {**body["criteria"], "facets": {"cuisine": ["martian"]}},
        },
        headers=h,
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "unknown_facet_option"


async def test_two_field_workspace_keeps_shift_filters_visible(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    assert (
        await c.post(W + "/industries", json={"key": "hospitality"}, headers=h)
    ).status_code == 200
    experience = (await c.get(W + "/experience", headers=h)).json()
    assert experience["primary"] == "technology"
    assert experience["manifest"]["states"]["shifts"] == "visible"
    assert experience["manifest"]["states"]["facets"] == "visible"
    assert "hospitality" in experience["packs"]


async def test_workspace_industries_are_tenant_isolated(tenancy):
    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO workspace_industries (workspace_id, industry_key, is_primary) "
                "VALUES (:w, 'technology', true) ON CONFLICT DO NOTHING"
            ),
            {"w": tenancy.ws_a},
        )
        await conn.execute(
            text(
                "INSERT INTO workspace_industries (workspace_id, industry_key, is_primary) "
                "VALUES (:w, 'technology', true) ON CONFLICT DO NOTHING"
            ),
            {"w": tenancy.ws_b},
        )
    await engine.dispose()

    app_engine = create_async_engine(TEST_DB_URL)
    async with app_engine.begin() as conn:
        await conn.execute(
            text("SELECT set_config('app.workspace_id', :w, true)"),
            {"w": str(tenancy.ws_a)},
        )
        await conn.execute(
            text("SELECT set_config('app.user_id', :u, true)"),
            {"u": str(tenancy.users["a_owner"])},
        )
        visible = (
            (
                await conn.execute(
                    text("SELECT workspace_id FROM workspace_industries ORDER BY workspace_id")
                )
            )
            .scalars()
            .all()
        )
    await app_engine.dispose()
    assert visible == [tenancy.ws_a]
