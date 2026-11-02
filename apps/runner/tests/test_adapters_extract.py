"""Unit tests for ATS adapters and extract helpers (no browser)."""

from __future__ import annotations

from pathlib import Path

from runner.adapters.base import detect_adapter
from runner.extract import (
    already_applied,
    looks_like_confirmation,
    looks_like_login,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_detect_adapters():
    assert detect_adapter("https://boards.greenhouse.io/x/jobs/1").key == "greenhouse"
    assert detect_adapter("https://jobs.lever.co/x").key == "lever"
    assert detect_adapter("https://jobs.ashbyhq.com/x").key == "ashby"
    assert detect_adapter("https://company.myworkdayjobs.com/en-US/x").key == "workday"
    assert detect_adapter("https://example.com/apply").key == "generic"


def test_confirmation_and_login_helpers():
    gh = detect_adapter("https://boards.greenhouse.io/x")
    assert looks_like_confirmation(
        "Thank you! We received your application.", gh.confirmation_needles
    )
    assert looks_like_login("Please sign in to continue", gh.login_needles)
    assert already_applied("You have already applied to this position")
    # A generic "thank you" is not proof of a submitted application.
    assert not looks_like_confirmation(
        "Thank you for your interest in Acme", gh.confirmation_needles
    )


def test_fixtures_parseable():
    for name in ("greenhouse.html", "lever.html", "ashby.html", "sensitive.html"):
        html = (FIXTURES / name).read_text()
        assert "<form" in html.lower()
        assert "input" in html.lower()
