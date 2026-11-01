"""Application status state machine unit tests."""

from __future__ import annotations

import pytest

from app.applications.status import assert_transition, normalize
from app.core.errors import AppError


def test_normalize_applied():
    assert normalize("applied") == "submitted"


def test_allowed_forward():
    assert_transition("ready", "submitted")
    assert_transition("submitted", "responded")
    assert_transition("responded", "interview")


def test_regression_requires_note():
    with pytest.raises(AppError):
        assert_transition("interview", "rejected", note="")
    assert_transition("interview", "rejected", note="Company paused the process")


def test_invalid_jump():
    with pytest.raises(AppError):
        assert_transition("ready", "offer")
