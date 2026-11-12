"""Unit tests for posting match-term detection and verdicts."""

from __future__ import annotations

from app.matching.highlights import build_match_terms
from app.taxonomy.skills import canonical_skill_label, find_skill_terms


def _labels(text: str) -> set[str]:
    return {hit.label for hit in find_skill_terms(text)}


def test_detection_respects_word_boundaries():
    labels = _labels(
        "We use JavaScript. Google is not the language. reaction time matters. We rest well."
    )
    assert "JavaScript" in labels
    assert "Java" not in labels
    assert "Go" not in labels
    assert "React" not in labels
    assert "REST" not in labels


def test_detection_handles_aliases_and_suffixes():
    labels = _labels("Node.js and NodeJS, K8s, Postgres, React.js, .NET and C#.")
    assert {"Node.js", "Kubernetes", "PostgreSQL", "React", ".NET", "C#"} <= labels


def test_canonical_labels_fold_spelling_variants():
    assert canonical_skill_label("react.js") == "React"
    assert canonical_skill_label("Postgres") == "PostgreSQL"
    assert canonical_skill_label("TS") == "TypeScript"
    assert canonical_skill_label("Customer Support") == "Customer Support"


def test_case_sensitive_names_ignore_ordinary_words():
    assert "Go" not in _labels("We go fast and rest well.")
    assert "REST" not in _labels("We rest well.")


def test_blocked_phrases_do_not_read_as_skills():
    assert "Excel" not in _labels("Excel at customer service.")
    assert "Go" not in _labels("Go to market quickly.")
    assert "Excel" in _labels("Advanced Excel and PowerPoint.")
    assert "Go" in _labels("Go developer with Kubernetes.")


def test_profile_skill_case_sensitivity_is_preserved():
    assert build_match_terms(description="We go fast.", profile_skills=["Go"]) == []
    terms = build_match_terms(description="We use Go and Go modules.", profile_skills=["Go"])
    assert terms[0]["label"] == "Go"
    assert terms[0]["verdict"] == "met"


def test_match_term_keys_are_unique_for_punctuation_names():
    terms = build_match_terms(
        description="We use C# and C++ and .NET.",
        profile_skills=[],
    )
    keys = [t["key"] for t in terms]
    labels = {t["label"] for t in terms}
    assert {".NET", "C#", "C++"} <= labels
    assert len(keys) == len(set(keys))


def test_match_terms_mark_profile_evidence():
    terms = build_match_terms(
        description="Senior React engineer with Python and Node.js. AWS required.",
        profile_skills=["React", "Python", "Node"],
    )
    by_label = {t["label"]: t for t in terms}
    assert by_label["React"]["verdict"] == "met"
    assert by_label["Python"]["verdict"] == "met"
    assert by_label["Node.js"]["verdict"] == "met"
    assert by_label["Node.js"]["evidence"] == "Node"
    assert by_label["AWS"]["verdict"] == "gap"
    assert by_label["AWS"]["evidence"] is None


def test_match_terms_use_qualification_partial_verdict():
    terms = build_match_terms(
        description="Experience with machine learning is required.",
        profile_skills=[],
        qualifications=[
            {
                "normalized": {"type": "skill", "name": "machine learning"},
                "verdict": "partial",
                "kind": "must",
            }
        ],
    )
    term = next(t for t in terms if t["label"] == "Machine Learning")
    assert term["verdict"] == "partial"


def test_match_terms_skip_excluded_skills():
    terms = build_match_terms(
        description="React and Vue and Python.",
        profile_skills=["React", "Vue", "Python"],
        criteria={"skills": {"must": [], "nice": [], "exclude": ["Vue"]}},
    )
    labels = {t["label"] for t in terms}
    assert "Vue" not in labels
    assert {"React", "Python"} <= labels


def test_match_terms_are_empty_without_a_description():
    assert build_match_terms(description="", profile_skills=["Python"]) == []
    assert build_match_terms(description="   ", profile_skills=["Python"]) == []


def test_required_gaps_sort_before_nice_gaps():
    terms = build_match_terms(
        description="We use React, Figma, Jira, AWS, and Kubernetes.",
        profile_skills=[],
        criteria={"skills": {"must": ["AWS"], "nice": [], "exclude": []}},
    )
    verdicts = [t["verdict"] for t in terms]
    assert verdicts == sorted(verdicts, key=lambda v: {"met": 0, "partial": 1, "gap": 2}[v])
    assert terms[0]["label"] == "AWS"
