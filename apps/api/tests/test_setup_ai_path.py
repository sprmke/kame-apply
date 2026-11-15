"""Setup with AI: the whole pipeline through a fake structured runner, no key required."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.service import StructuredAiResult
from app.core.config import Settings
from app.main import create_app
from app.onboarding.schemas import (
    SearchPlanV2Out,
    SearchVariantOut,
    SetupSignalsOut,
    StatedSignalOut,
)
from app.profiles.parse_schema import ProfileExtract
from app.tracks.criteria import TitleSpec
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

RESUME = """ANA REYES
Customer Support Lead
Manila, Philippines
ana.reyes@example.com
US citizen

Summary
Support lead with 6 years in SaaS onboarding and a track record of cutting response times.

Notice period: 30 days

Skills: onboarding, Zendesk, team leadership, QA, SQL

Experience
2020 - 2025 Support Lead at Acme
Cut response times by 40 percent.

Education
2014 - 2018 BS Psychology, University of the Philippines
"""

S = "/api/v1/onboarding/setups"


def _profile_extract() -> ProfileExtract:
    return ProfileExtract.model_validate(
        {
            "display_name": {"value": "Ana Reyes", "confidence": 0.95, "span": "ANA REYES"},
            "headline": {
                "value": "Customer Support Lead",
                "confidence": 0.9,
                "span": "Customer Support Lead",
            },
            "location": {"value": "Manila, Philippines", "confidence": 0.9},
            "summary": {
                "value": "Support lead with 6 years in SaaS onboarding.",
                "confidence": 0.8,
            },
            "experiences": [
                {
                    "company": "Acme",
                    "title": "Support Lead",
                    "start_date": "2020-01-01",
                    "end_date": "2025-01-01",
                    "description": "Cut response times by 40 percent.",
                    "bullets": [
                        {"text": "Cut response times by 40 percent", "skills": ["Zendesk"]}
                    ],
                    "confidence": 0.9,
                    "span": "2020 - 2025 Support Lead at Acme",
                }
            ],
            # Planted fake fact: not in the resume, must be dropped by grounding.
            "skills": [{"name": "Zendesk"}, {"name": "Kubernetes"}],
        }
    )


def _signals() -> SetupSignalsOut:
    return SetupSignalsOut(
        signals=[
            StatedSignalOut(kind="notice", value="30 days", quote="Notice period: 30 days"),
            StatedSignalOut(
                kind="work_authorization",
                value="US citizen",
                quote="US citizen",
                country="US",
            ),
            # Planted fake quote: not in the resume, must be dropped.
            StatedSignalOut(
                kind="salary", value="PHP 1,000,000", quote="Expected salary: PHP 1,000,000"
            ),
        ]
    )


def _plan() -> SearchPlanV2Out:
    return SearchPlanV2Out(
        variants=[
            SearchVariantOut(
                variant="same_role",
                titles=[TitleSpec(title="Support Operations Lead", synonyms=["Support Ops Lead"])],
                core_skills=["Zendesk", "Kubernetes"],
                nice_skills=["Salesforce"],
                seniority=["lead"],
                work_modes=["remote"],
            )
        ]
    )


async def _runner(_ctx, _settings, **kwargs):
    feature = kwargs.get("feature")
    if feature == "profile_extract":
        output = _profile_extract()
    elif feature == "setup_signals":
        output = _signals()
    elif feature == "search_plan_v2":
        output = _plan()
    else:  # pragma: no cover - test guard
        raise AssertionError(feature)
    return StructuredAiResult(
        output=output,
        provider="fake",
        model="fake",
        input_tokens=10,
        output_tokens=5,
        cost_micros=1,
    )


@pytest.fixture
async def ai_env():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        app.state.run_structured = _runner
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://ai"
        ) as c:
            yield c


async def test_ai_path_builds_facts_signals_and_a_search(ai_env):
    c = ai_env
    me = await signup(c)
    r = await c.post(S, json={"text": RESUME, "timezone": "Asia/Manila"}, headers=me.h(me.personal))
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "ready", body["steps"]
    assert body["steps"]["extract_profile"]["source"] == "ai"
    assert body["steps"]["stated_signals"]["source"] == "ai"
    assert body["steps"]["plan_searches"]["source"] == "ai"
    assert "ai_off_basics_only" not in body["bundle"]["notices"]

    items = body["bundle"]["items"]
    by_target: dict[str, list] = {}
    for item in items:
        by_target.setdefault(item["target"], []).append(item)

    assert by_target["profile.display_name"][0]["value"] == "Ana Reyes"
    assert by_target["profile.experience"][0]["value"]["company"] == "Acme"

    skill_names = {item["value"]["name"] for item in by_target["profile.skill"]}
    assert "Zendesk" in skill_names
    assert "Kubernetes" not in skill_names  # planted fact, no quote in the resume

    notice = by_target["answers.notice_period"][0]
    assert notice["value"]["answer"] == "30 days"
    assert notice["source"] == "resume"

    auth = by_target["answers.work_authorization.US"][0]
    assert auth["value"]["answer"] == "US citizen"

    salary = by_target["answers.salary_expectation"][0]
    assert salary["source"] == "default"
    assert "1,000,000" not in str(salary["value"])

    searches = body["bundle"]["searches"]
    assert len(searches) == 1
    search = searches[0]
    assert search["variant"] == "same_role"
    assert search["criteria"]["titles"][0]["title"] == "Support Operations Lead"
    assert search["criteria"]["skills"]["must"] == ["Zendesk"]
    assert "Kubernetes" not in search["criteria"]["skills"]["must"]
    assert search["criteria"]["work_modes"] == ["remote"]
    assert search["criteria"]["locations"][0]["place"] == "Manila, Philippines"
    assert search["schedule"]["preset"] == "every_4_hours"
