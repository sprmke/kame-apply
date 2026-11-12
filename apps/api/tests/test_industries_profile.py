"""IND-6: profile facets CRUD + RLS, and pack-filtered answer keys."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DB_URL
from tests.test_ai import env  # noqa: F401
from tests.test_workspaces import signup


async def _profile(c, who) -> str:
    r = await c.post(
        "/api/v1/profiles", json={"display_name": "Ana Reyes"}, headers=who.h(who.personal)
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_profile_facets_create_list_delete_and_full_profile(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    profile_id = await _profile(c, me)
    base = f"/api/v1/profiles/{profile_id}"

    created = await c.post(
        base + "/facets",
        json={"facet_key": "cuisine", "value": "filipino"},
        headers=h,
    )
    assert created.status_code == 201, created.text
    facet_id = created.json()["id"]
    assert created.json()["facet_key"] == "cuisine"

    duplicate = await c.post(
        base + "/facets",
        json={"facet_key": "cuisine", "value": "filipino"},
        headers=h,
    )
    assert duplicate.status_code == 409

    listed = await c.get(base + "/facets", headers=h)
    assert [row["value"] for row in listed.json()] == ["filipino"]

    full = await c.get(base, headers=h)
    assert full.status_code == 200
    assert [row["value"] for row in full.json()["facets"]] == ["filipino"]

    deleted = await c.delete(f"{base}/facets/{facet_id}", headers=h)
    assert deleted.status_code == 200
    assert (await c.get(base + "/facets", headers=h)).json() == []


async def test_profile_facets_are_tenant_isolated(env, tenancy):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    profile_id = await _profile(c, me)
    created = await c.post(
        f"/api/v1/profiles/{profile_id}/facets",
        json={"facet_key": "station", "value": "grill"},
        headers=h,
    )
    assert created.status_code == 201

    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("SELECT set_config('app.workspace_id', :w, true)"),
            {"w": str(tenancy.ws_b)},
        )
        await conn.execute(
            text("SELECT set_config('app.user_id', :u, true)"),
            {"u": str(tenancy.users["b_owner"])},
        )
        count = (await conn.execute(text("SELECT count(*) FROM profile_facets"))).scalar_one()
    await engine.dispose()
    assert count == 0


async def test_portfolio_image_upload_strips_exif(env):  # noqa: F811
    import io

    from PIL import Image

    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    profile_id = await _profile(c, me)

    image = Image.new("RGB", (40, 30), (190, 120, 70))
    exif = image.getexif()
    exif[0x010F] = "TestCamera"  # Make
    exif[0x0110] = "TestModel"  # Model
    raw = io.BytesIO()
    image.save(raw, format="JPEG", exif=exif.tobytes())

    uploaded = await c.post(
        f"/api/v1/profiles/{profile_id}/documents",
        files={"file": ("dish.jpg", raw.getvalue(), "image/jpeg")},
        data={"kind": "portfolio"},
        headers=h,
    )
    assert uploaded.status_code == 201, uploaded.text
    doc = uploaded.json()
    assert doc["status"] == "ready"
    assert doc["mime"] == "image/jpeg"

    storage = c._transport.app.state.storage  # type: ignore[attr-defined]
    key = next(k for k in storage.objects if str(doc["id"]) in k)
    stored, _ = storage.objects[key]
    with Image.open(io.BytesIO(stored)) as clean:
        clean_exif = clean.getexif()
        assert 0x010F not in clean_exif
        assert 0x0110 not in clean_exif


async def test_answer_keys_follow_the_workspace_fields(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    profile_id = await _profile(c, me)
    url = f"/api/v1/profiles/{profile_id}/answers/keys"

    tech = {row["key"] for row in (await c.get(url, headers=h)).json()}
    assert "github_url" in tech
    assert "food_safety_certificate" not in tech

    assert (
        await c.post("/api/v1/workspace/industries", json={"key": "hospitality"}, headers=h)
    ).status_code == 200

    both = {row["key"] for row in (await c.get(url, headers=h)).json()}
    assert "food_safety_certificate" in both
    assert "shift_preference" in both
    assert "github_url" in both  # Technology still adds it

    assert (await c.delete("/api/v1/workspace/industries/technology", headers=h)).status_code == 200

    hospitality = {row["key"] for row in (await c.get(url, headers=h)).json()}
    assert "food_safety_certificate" in hospitality
    assert "github_url" not in hospitality
