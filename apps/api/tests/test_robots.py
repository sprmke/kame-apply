"""robots.txt is respected for career-page crawling (PRD P5)."""

import pytest

from kame_core.sources import http
from kame_core.sources.http import robots_allows_text

ROBOTS = """
User-agent: *
Disallow: /careers/private
Allow: /careers

User-agent: KameApplyBot
Disallow: /careers/blocked
"""


def test_robots_allows_public_career_pages():
    assert robots_allows_text(ROBOTS, "https://example.com/careers/engineer") is True
    assert robots_allows_text(ROBOTS, "https://example.com/jobs/1") is True


def test_robots_blocks_disallowed_paths():
    # A specific user-agent group overrides the generic `*` group entirely.
    assert robots_allows_text(ROBOTS, "https://example.com/careers/blocked/1") is False
    assert robots_allows_text(ROBOTS, "https://example.com/careers/private/1") is True
    # Other crawlers follow the `*` group.
    assert (
        robots_allows_text(ROBOTS, "https://example.com/careers/private/1", user_agent="OtherBot")
        is False
    )


def test_missing_robots_allows():
    assert robots_allows_text("", "https://example.com/careers/1") is True


class _FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


class _FakeClient:
    calls = 0
    status = 200
    body = "User-agent: *\nDisallow: /private\n"

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None):
        type(self).calls += 1
        return _FakeResponse(type(self).status, type(self).body)


@pytest.mark.asyncio
async def test_robots_allowed_fetches_once_and_caches(monkeypatch):
    _FakeClient.calls = 0
    _FakeClient.status = 200
    monkeypatch.setattr(http.httpx, "AsyncClient", _FakeClient)
    http.reset_politeness_state()

    assert await http.robots_allowed("https://example.com/public") is True
    assert await http.robots_allowed("https://example.com/private/1") is False
    assert _FakeClient.calls == 1  # second call hit the host cache


@pytest.mark.asyncio
async def test_robots_allowed_treats_missing_file_as_allow(monkeypatch):
    _FakeClient.calls = 0
    _FakeClient.status = 404
    monkeypatch.setattr(http.httpx, "AsyncClient", _FakeClient)
    http.reset_politeness_state()

    assert await http.robots_allowed("https://missing.example/careers") is True
