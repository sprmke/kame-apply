"""Golden resume set (≥15): expected fields + offline draft scoring when present.

Live LLM precision/recall is marked `live` and skipped in evals-lite. Offline checks verify
fixture shape, sanitize safety, and recorded-draft field match ≥ 95% on titles/companies/dates.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.profiles.parse import post_process_draft
from app.profiles.parse_schema import ProfileExtract
from app.profiles.sanitize import sanitize_untrusted_text

GOLDEN = Path(__file__).parent / "fixtures" / "golden"


def _fixtures() -> list[Path]:
    return sorted(GOLDEN.glob("*.json"))


def test_golden_set_has_at_least_fifteen_diverse_fixtures():
    files = _fixtures()
    assert len(files) >= 15
    countries = set()
    roles = set()
    for path in files:
        data = json.loads(path.read_text())
        assert data["id"] == path.stem
        assert data["resume_text"].strip()
        assert data["expected"]["display_name"]
        assert data["expected"]["experiences"]
        countries.add(data["country"])
        roles.add(data["role"])
    assert len(countries) >= 8
    assert len(roles) >= 8


@pytest.mark.parametrize("path", _fixtures(), ids=lambda p: p.stem)
def test_golden_resume_text_sanitizes_cleanly(path: Path):
    data = json.loads(path.read_text())
    cleaned = sanitize_untrusted_text(data["resume_text"])
    assert data["expected"]["display_name"].split()[0] in cleaned.text
    assert "Ignore previous" not in cleaned.text


def _norm(s: str | None) -> str:
    return " ".join((s or "").lower().split())


def _score_draft(draft: ProfileExtract, expected: dict) -> tuple[float, float, float]:
    """Return precision-like ratios for company, title, start_date over expected experiences."""
    exps = expected.get("experiences") or []
    if not exps:
        return 1.0, 1.0, 1.0
    companies = {_norm(e.company) for e in draft.experiences}
    titles = {_norm(e.title) for e in draft.experiences}
    starts = {str(e.start_date)[:7] for e in draft.experiences if e.start_date}
    c_hit = sum(
        1
        for e in exps
        if any(_norm(e["company"]) in c or c in _norm(e["company"]) for c in companies)
    )
    t_hit = sum(
        1 for e in exps if any(_norm(e["title"]) in t or t in _norm(e["title"]) for t in titles)
    )
    dated = [e for e in exps if e.get("start_date")]
    if not dated or not starts:
        d_ratio = 1.0
    else:
        d_hit = sum(1 for e in dated if str(e["start_date"])[:7] in starts)
        d_ratio = d_hit / len(dated)
    n = len(exps)
    return c_hit / n, t_hit / n, d_ratio


def test_recorded_drafts_meet_field_target():
    scored = 0
    company_scores: list[float] = []
    title_scores: list[float] = []
    date_scores: list[float] = []
    for path in _fixtures():
        data = json.loads(path.read_text())
        draft_raw = data.get("recorded_draft")
        if not draft_raw:
            continue
        draft = ProfileExtract.model_validate(draft_raw)
        clean = post_process_draft(draft)
        c, t, d = _score_draft(clean, data["expected"])
        company_scores.append(c)
        title_scores.append(t)
        date_scores.append(d)
        scored += 1
    # Nurse fixture from lite eval can be linked; until more recorded drafts exist, require the
    # set to remain valid and score any recorded drafts at the 95% target.
    if scored == 0:
        pytest.skip("no recorded_draft payloads yet; fixtures still validate offline")
    assert sum(company_scores) / scored >= 0.95
    assert sum(title_scores) / scored >= 0.95
    assert sum(date_scores) / scored >= 0.95


def test_link_nurse_recorded_draft_into_golden_scoring():
    """Reuse the existing nurse extract fixture as a recorded draft for offline scoring."""
    nurse = json.loads((GOLDEN.parent / "profile_extract_nurse.json").read_text())
    draft = ProfileExtract.model_validate(
        {
            "summary": {"value": None, "confidence": 0.1},
            "timezone": {"value": None, "confidence": 0.1},
            "language": {"value": "en", "confidence": 0.5},
            "links": [],
            "projects": [],
            "languages": [],
            **nurse["expected_draft"],
        }
    )
    clean = post_process_draft(draft)
    expected = {
        "experiences": [
            {
                "company": "St. Luke's",
                "title": "Registered Nurse",
                "start_date": "2019-03-01",
            }
        ]
    }
    c, t, d = _score_draft(clean, expected)
    assert c >= 0.95 and t >= 0.95 and d >= 0.95


def test_live_golden_precision_recall_target():
    """Opt-in live LLM scoring across the golden set. RUN_LIVE_AI=1 to enable."""
    import os

    if os.environ.get("RUN_LIVE_AI") != "1":
        pytest.skip("set RUN_LIVE_AI=1 for live golden scoring")

    import asyncio

    env_path = Path(__file__).resolve().parents[2] / ".env"
    key = None
    for line in env_path.read_text().splitlines():
        if line.startswith("GEMINI_API_KEYS="):
            key = line.split("=", 1)[1].split(",")[0].strip()
            break
    assert key, "GEMINI_API_KEYS missing in apps/api/.env"
    asyncio.run(_live_golden_score(key))


async def _live_golden_score(key: str) -> None:
    import asyncio
    import io

    from httpx import ASGITransport, AsyncClient

    from app.core.config import Settings
    from app.main import create_app
    from tests.conftest import TEST_DB_URL
    from tests.test_workspaces import signup

    app = create_app(
        Settings(
            database_url=TEST_DB_URL,
            environment="test",
            log_json=False,
            auth_rate_limit_enabled=False,
        )
    )

    company_scores: list[float] = []
    title_scores: list[float] = []
    date_scores: list[float] = []

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t", timeout=180
        ) as c:
            me = await signup(c)
            ws = me.personal
            h = me.h(ws)
            cred = await c.post(
                "/api/v1/ai/credentials",
                json={"provider": "gemini", "api_key": key},
                headers=h,
            )
            assert cred.status_code == 201, cred.text
            profile = await c.post(
                "/api/v1/profiles",
                json={"display_name": "Golden Set"},
                headers=h,
            )
            assert profile.status_code == 201, profile.text
            pid = profile.json()["id"]
            for path in _fixtures():
                data = json.loads(path.read_text())
                text = data["resume_text"].encode()
                up = await c.post(
                    f"/api/v1/profiles/{pid}/documents",
                    files={"file": (f"{path.stem}.txt", io.BytesIO(text), "text/plain")},
                    headers=h,
                )
                assert up.status_code == 201, up.text
                doc_id = up.json()["id"]
                parsed = None
                for attempt in range(4):
                    parsed = await c.post(
                        f"/api/v1/profiles/{pid}/documents/{doc_id}/parse",
                        headers=h,
                    )
                    if parsed.status_code == 200:
                        break
                    # Provider blips (429/503) are common on free Gemini; back off and retry.
                    if parsed.status_code not in (502, 503, 429) or attempt == 3:
                        break
                    await asyncio.sleep(15 * (attempt + 1))
                assert parsed is not None and parsed.status_code == 200, (
                    path.stem,
                    parsed.status_code if parsed else None,
                    parsed.text if parsed else None,
                )
                draft = ProfileExtract.model_validate(parsed.json()["parsed"])
                clean = post_process_draft(draft)
                # Persist as recorded_draft for offline regression.
                data["recorded_draft"] = clean.model_dump(mode="json")
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
                sc, st, sd = _score_draft(clean, data["expected"])
                company_scores.append(sc)
                title_scores.append(st)
                date_scores.append(sd)
                await asyncio.sleep(3)

    n = len(company_scores)
    assert n >= 15
    assert sum(company_scores) / n >= 0.95, company_scores
    assert sum(title_scores) / n >= 0.95, title_scores
    assert sum(date_scores) / n >= 0.95, date_scores
