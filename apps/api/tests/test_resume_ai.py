"""AI-backed resume critique and cover letter: grounding, merge, and fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import AppError
from app.main import create_app
from app.resumes.cover_letter_ai import AiCoverLetter, draft_cover_letter_ai
from app.resumes.critique import critique_resume
from app.resumes.critique_ai import AiCritique, AiCritiqueFinding, enrich_critique
from app.resumes.from_profile import build_from_profile
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"
R = "/api/v1/resumes"

SETTINGS = Settings(database_url=TEST_DB_URL, environment="test", log_json=False)


@dataclass
class FakeResult:
    output: Any
    provider: str = "fake"
    model: str = "fake-1"
    input_tokens: int = 10
    output_tokens: int = 10
    cost_micros: int = 1


def fake_runner(output: Any):
    async def runner(ctx, settings, **kwargs):
        return FakeResult(output)

    return runner


def failing_runner(code: str = "ai_not_configured"):
    async def runner(ctx, settings, **kwargs):
        raise AppError(code, "no ai", 409)

    return runner


def _facts() -> dict[str, Any]:
    return {
        "id": "p1",
        "display_name": "Ada Lovelace",
        "headline": "Backend Engineer",
        "summary": "Builds APIs",
        "location": "Remote",
        "email": "ada@example.com",
        "phone": None,
        "links": [],
        "work_authorization": {},
        "experiences": [
            {
                "id": "e1",
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2019-01-01",
                "end_date": None,
                "is_current": True,
                "description": None,
            }
        ],
        "projects": [],
        "bullets": [
            {
                "id": "b1",
                "experience_id": "e1",
                "project_id": None,
                "text": "Built FastAPI services in Python for 12 real teams",
                "metrics": [],
                "skills": ["Python", "FastAPI"],
            }
        ],
        "skills": [
            {"id": "s1", "name": "Python", "level": None, "years": None},
            {"id": "s2", "name": "FastAPI", "level": None, "years": None},
        ],
        "education": [],
        "certifications": [],
    }


# --- critique -----------------------------------------------------------------


async def test_ai_critique_merges_without_lowering_known_scores():
    content = build_from_profile(_facts(), target_role="Backend Engineer")
    base = critique_resume(content, target_role="Backend Engineer")
    base["categories"]["parseability"]["score"] = 2
    ai = AiCritique(
        categories={"parseability": 5, "impact": 4, "made_up": 5},
        findings=[
            AiCritiqueFinding(category="impact", message="Add outcomes", impact=4, line_id="nope"),
            AiCritiqueFinding(
                category="specificity",
                message="Name the stack in the summary",
                impact=3,
                line_id=content.summary.id if content.summary else None,
            ),
        ],
        summary="Solid base, needs sharper outcomes.",
    )
    out = await enrich_critique(
        None,  # type: ignore[arg-type]
        SETTINGS,
        report=base,
        content=content,
        target_role="Backend Engineer",
        run_structured=fake_runner(ai),
    )
    # The model cannot raise a score the deterministic pass already lowered.
    assert out["categories"]["parseability"]["score"] == 2
    assert out["categories"]["impact"]["score"] == 4
    assert "made_up" not in out["categories"]
    by_message = {f["message"]: f for f in out["findings"]}
    assert by_message["Add outcomes"]["line_id"] is None
    assert content.summary is not None
    assert by_message["Name the stack in the summary"]["line_id"] == content.summary.id
    assert out["ai"]["summary"].startswith("Solid base")
    assert len(out["top_fixes"]) <= 5


async def test_ai_critique_falls_back_without_a_key_or_budget():
    content = build_from_profile(_facts())
    base = critique_resume(content, target_role="Backend Engineer")
    for code in ("ai_not_configured", "budget_reached", "ai_provider_error"):
        out = await enrich_critique(
            None,  # type: ignore[arg-type]
            SETTINGS,
            report=base,
            content=content,
            run_structured=failing_runner(code),
        )
        assert out == base
        assert "ai" not in out


# --- cover letter -------------------------------------------------------------

GOOD_LETTER = """Dear hiring team,

I am applying for the Backend Engineer role at Acme. I have built FastAPI services in Python for real teams, and I care about making tradeoffs visible rather than hiding them. In my recent work I wrote services that other engineers relied on daily, and I documented the decisions so the next person could pick them up without guessing. I also worked closely with product and support to keep scope honest when a deadline moved, and I kept the team informed about what would slip and why. The posting describes a team that values careful delivery, and that is the kind of work I want to keep doing. I like problems where the constraints are real, because that is where clear communication and small, safe steps matter most. I would welcome a conversation about the role and about how I can help Acme ship steadily without overstating what I have done.

Ada"""


def _letter_job() -> dict[str, Any]:
    return {
        "title": "Backend Engineer",
        "company_name": "Acme",
        "description_text": "We value careful delivery and clear communication.",
    }


def _letter_matches() -> list[dict[str, Any]]:
    return [
        {
            "text": "Built FastAPI services in Python for 12 real teams",
            "evidence_quote": "Built FastAPI services in Python for 12 real teams",
            "evidence_ref": "b1",
        }
    ]


async def test_ai_cover_letter_is_verified_and_bounded():
    out = await draft_cover_letter_ai(
        None,  # type: ignore[arg-type]
        SETTINGS,
        facts=_facts(),
        job=_letter_job(),
        matches=_letter_matches(),
        run_structured=fake_runner(AiCoverLetter(text=GOOD_LETTER)),
    )
    assert out is not None
    assert out["source"] == "ai"
    assert 150 <= out["word_count"] <= 250
    assert "Dear hiring team," in out["content"]
    assert out["evidence_refs"] == ["b1"]


async def test_ai_cover_letter_rejects_invented_entities_and_numbers():
    invented = GOOD_LETTER.replace("at Acme", "at Globex")
    out = await draft_cover_letter_ai(
        None,  # type: ignore[arg-type]
        SETTINGS,
        facts=_facts(),
        job=_letter_job(),
        matches=_letter_matches(),
        run_structured=fake_runner(AiCoverLetter(text=invented)),
    )
    assert out is None

    numbered = GOOD_LETTER.replace("for real teams", "for 12 teams")
    out2 = await draft_cover_letter_ai(
        None,  # type: ignore[arg-type]
        SETTINGS,
        facts=_facts(),
        job=_letter_job(),
        matches=_letter_matches(),
        run_structured=fake_runner(AiCoverLetter(text=numbered)),
    )
    # 12 is in the evidence quote here, so the number itself is grounded.
    assert out2 is not None

    ungrounded = GOOD_LETTER.replace("for real teams", "for 47 teams")
    out3 = await draft_cover_letter_ai(
        None,  # type: ignore[arg-type]
        SETTINGS,
        facts=_facts(),
        job=_letter_job(),
        matches=_letter_matches(),
        run_structured=fake_runner(AiCoverLetter(text=ungrounded)),
    )
    assert out3 is None


async def test_ai_cover_letter_falls_back_on_short_text_or_soft_stop():
    short = "Dear hiring team,\n\nI am applying. Ada"
    out = await draft_cover_letter_ai(
        None,  # type: ignore[arg-type]
        SETTINGS,
        facts=_facts(),
        job=_letter_job(),
        matches=_letter_matches(),
        run_structured=fake_runner(AiCoverLetter(text=short)),
    )
    assert out is None

    stopped = await draft_cover_letter_ai(
        None,  # type: ignore[arg-type]
        SETTINGS,
        facts=_facts(),
        job=_letter_job(),
        matches=_letter_matches(),
        run_structured=failing_runner("budget_reached"),
    )
    assert stopped is None


# --- API integration ----------------------------------------------------------


@pytest.fixture
async def env_ai():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, app


async def _seed_resume(c, me):
    h = me.h(me.personal)
    p = (
        await c.post(P, json={"display_name": "Ada Lovelace", "headline": "Engineer"}, headers=h)
    ).json()
    await c.patch(f"{P}/{p['id']}", json={"summary": "Builds analytical engines"}, headers=h)
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences",
            json={
                "company": "Analytical Engines",
                "title": "Engineer",
                "start_date": "2019-01-01",
                "is_current": True,
            },
            headers=h,
        )
    ).json()
    await c.post(
        f"{P}/{p['id']}/bullets",
        json={"experience_id": exp["id"], "text": "Wrote algorithms for 12 clients"},
        headers=h,
    )
    await c.post(f"{P}/{p['id']}/skills", json={"name": "Python"}, headers=h)
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Engineer",
                "nl_text": "engineer",
                "criteria": {
                    "schema_version": 1,
                    "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
                },
            },
            headers=h,
        )
    ).json()
    ver = (
        await c.post(
            R,
            json={"profile_id": p["id"], "track_id": track["id"], "label": "Base"},
            headers=h,
        )
    ).json()
    return h, ver["id"]


async def test_critique_route_uses_the_injected_ai_runner(env_ai):
    c, app = env_ai
    me = await signup(c)
    h, version_id = await _seed_resume(c, me)
    app.state.run_structured = fake_runner(
        AiCritique(categories={"impact": 4}, findings=[], summary="Tighten outcomes.")
    )
    r = await c.post(f"{R}/{version_id}/critique", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai"]["summary"] == "Tighten outcomes."
    assert body["categories"]["impact"]["score"] == 4


async def test_critique_route_stays_deterministic_without_ai(env_ai):
    c, app = env_ai
    me = await signup(c)
    h, version_id = await _seed_resume(c, me)
    app.state.run_structured = failing_runner("ai_not_configured")
    r = await c.post(f"{R}/{version_id}/critique", headers=h)
    assert r.status_code == 200, r.text
    assert r.json().get("ai") is None
