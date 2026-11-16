"""Industry hint: the field of work a resume points at, as a chip, never a switch."""

from __future__ import annotations

import uuid

from app.onboarding.bundle import Reading, build_bundle
from app.onboarding.derive import industry


def _reading(text: str, headline: str = "") -> Reading:
    return Reading(text=text, headline=headline)


def test_chef_resume_points_at_hospitality():
    hint = industry.detect(
        _reading(
            "Sous chef de partie. HACCP certified. Managed a brigade of eight in Dubai.",
            headline="Sous chef",
        )
    )
    assert hint is not None
    assert hint.pack_key == "hospitality"
    assert hint.role_family == "kitchen"
    assert hint.confidence >= 0.7


def test_engineer_resume_points_at_technology():
    hint = industry.detect(
        _reading(
            "Senior frontend engineer building React and TypeScript applications.",
            headline="Senior Frontend Engineer",
        )
    )
    assert hint is not None
    assert hint.pack_key == "technology"


def test_unmatched_resume_returns_none():
    assert industry.detect(_reading("Gardener with three years on a private estate.")) is None


def test_empty_reading_returns_none():
    assert industry.detect(_reading("")) is None


def test_bundle_carries_the_hint_with_its_label_key():
    bundle = build_bundle(
        reading=_reading(
            "Sous chef de partie. Food safety level 2. Kitchen team of six.",
            headline="Sous chef",
        ),
        document_id=uuid.uuid4(),
    )
    assert bundle.industry is not None
    assert bundle.industry.pack_key == "hospitality"
    assert bundle.industry.label_key == "industry.hospitality.label"


def test_bundle_without_a_hint_stays_none():
    bundle = build_bundle(
        reading=_reading("Gardener on a private estate."), document_id=uuid.uuid4()
    )
    assert bundle.industry is None
