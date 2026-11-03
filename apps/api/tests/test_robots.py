"""robots.txt is respected for career-page crawling (PRD P5)."""

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
