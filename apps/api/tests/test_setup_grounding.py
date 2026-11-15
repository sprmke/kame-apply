"""Grounding: unquoted claims disappear, settings stay, needs-you rows survive."""

from __future__ import annotations

import uuid
from typing import Any

from app.onboarding import schemas as s
from app.onboarding.evidence import evidence
from app.onboarding.grounding import ground_bundle, ground_items, normalize, quote_found

DOC = uuid.uuid4()
TEXT = "ANA REYES\nFrontend engineer\nManila, Philippines\nSkills: React, TypeScript\n"


def item(
    target: str,
    *,
    group: Any = "profile",
    source: Any = "resume",
    value: Any = "x",
    quote: str | None = None,
    needs_you: bool = False,
):
    refs = evidence(DOC, TEXT, quote) if quote is not None else []
    return s.SetupItem(
        id=target,
        group=group,
        target=target,
        kind="value",
        value=None if needs_you else value,
        source=source,
        evidence=refs,
        reason_key="setup.reason.test",
        needs_you=needs_you,
    )


def test_a_quoted_claim_is_kept():
    kept, dropped = ground_items([item("profile.headline", quote="Frontend engineer")], TEXT)
    assert len(kept) == 1 and dropped == 0


def test_a_claim_without_a_quote_is_dropped():
    kept, dropped = ground_items([item("profile.headline")], TEXT)
    assert kept == [] and dropped == 1


def test_a_quote_not_in_the_text_is_dropped():
    kept, dropped = ground_items([item("profile.headline", quote="Chief Marketing Officer")], TEXT)
    assert kept == [] and dropped == 1


def test_a_resume_item_with_an_empty_value_is_still_a_claim():
    kept, _ = ground_items([item("profile.headline", quote="")], TEXT)
    assert kept == []


def test_a_planted_fake_fact_is_dropped():
    dropped_items, dropped = ground_items(
        [item("profile.experience", value={"company": "Google"}, quote="Google")], TEXT
    )
    assert dropped_items == [] and dropped == 1


def test_settings_may_be_suggested():
    kept, _ = ground_items(
        [
            item("profile.timezone", source="suggested", value="Asia/Manila"),
            item("profile.language", source="suggested", value="en"),
        ],
        TEXT,
    )
    assert len(kept) == 2


def test_a_suggested_profile_fact_is_not_allowed():
    kept, dropped = ground_items([item("profile.headline", source="suggested", value="CTO")], TEXT)
    assert kept == [] and dropped == 1


def test_answers_may_use_defaults():
    kept, _ = ground_items(
        [
            item(
                "answers.salary_expectation",
                group="answers",
                source="default",
                value={"answer": "Open to discussion", "approved": False},
            )
        ],
        TEXT,
    )
    assert len(kept) == 1


def test_needs_you_rows_are_kept():
    kept, _ = ground_items([item("answers.notice_period", group="answers", needs_you=True)], TEXT)
    assert len(kept) == 1


def test_you_said_items_need_no_quote():
    kept, _ = ground_items([item("profile.headline", source="you_said", value="Designer")], TEXT)
    assert len(kept) == 1


def test_normalization_handles_case_space_and_bullets():
    assert quote_found(TEXT, "  FRONTEND   ENGINEER ")
    assert quote_found(TEXT, "- Skills: React, TypeScript")
    assert normalize("\ufb01nance") == "finance"
    assert normalize("\u201cManila\u201d") == '"manila"'


def test_bundle_counts_are_recomputed_after_a_drop():
    bundle = s.SetupBundle(
        items=[
            item("profile.headline", quote="Frontend engineer"),
            item("profile.summary", quote="Not in the text"),
        ],
        counts={"profile": 2, "needs_you": 0},
    )
    grounded, dropped = ground_bundle(bundle, TEXT)
    assert dropped == 1
    assert grounded.counts["profile"] == 1
