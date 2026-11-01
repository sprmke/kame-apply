"""Unit tests for CriteriaV1 helpers (no DB)."""

from app.tracks.compile_filter import compile_filter
from app.tracks.criteria import (
    CompanyFilter,
    CriteriaV1,
    RemoteEligibility,
    SalaryFilter,
    SkillSets,
    TitleSpec,
)
from app.tracks.currency import normalize_salary, to_monthly
from app.tracks.diff import diff_criteria
from app.tracks.invent_guard import invented_fields, strip_invented
from app.tracks.merge import CriteriaPatch, merge_criteria
from app.tracks.summary import summarize
from app.tracks.validate import validate_boolean_expr, validate_criteria


def test_summary_and_compile_roundtrip():
    c = CriteriaV1(
        titles=[TitleSpec(title="AI Engineer")],
        skills=SkillSets(must=["Python"], nice=["Go"], exclude=[]),
        work_modes=["remote"],
        remote_eligibility=RemoteEligibility(
            anywhere=True,
            regions=[],
            countries=[],
            timezone_overlap_hours=4,
            base_tz="Asia/Manila",
        ),
        companies=CompanyFilter(exclude_agencies=True),
    )
    sentence = summarize(c)
    assert "AI Engineer" in sentence
    assert "no agencies" in sentence
    compiled = compile_filter(c)
    assert compiled["version"] == 1
    ops = {p["op"] for p in compiled["predicates"]}
    assert "title_any" in ops
    assert "skills_all" in ops
    assert "company" in ops


def test_merge_does_not_drop_existing_and_honors_removals():
    current = CriteriaV1(
        titles=[TitleSpec(title="Software Engineer", synonyms=["SWE"])],
        skills=SkillSets(must=["Python", "Angular"], nice=[], exclude=[]),
    )
    patch = CriteriaPatch(
        titles=[TitleSpec(title="Platform Engineer")],
        skills=SkillSets(must=["Kubernetes"], nice=[], exclude=[]),
        removals=[{"path": "skills.must", "value": "Angular"}],
        companies={"exclude_agencies": True},
    )
    merged = merge_criteria(current, patch)
    titles = {t.title for t in merged.titles}
    assert "Software Engineer" in titles and "Platform Engineer" in titles
    assert "Angular" not in merged.skills.must
    assert "Python" in merged.skills.must and "Kubernetes" in merged.skills.must
    assert merged.companies.exclude_agencies is True
    changes = diff_criteria(current, merged)
    assert any(c["path"] == "titles" for c in changes)
    assert any("exclude_agencies" in c["path"] for c in changes)


def test_invent_guard_strips_salary_not_in_text():
    text = "Senior backend engineer in Berlin, hybrid"
    patch = CriteriaPatch(
        titles=[TitleSpec(title="Backend Engineer")],
        locations=[{"place": "Berlin"}],
        work_modes=["hybrid"],
        seniority=["senior"],
        salary={"min": 90000, "currency": "USD", "period": "year"},
    )
    invented = invented_fields(text, patch)
    assert "salary" in invented
    cleaned = strip_invented(patch, invented)
    assert cleaned.salary is None
    assert cleaned.titles is not None


def test_keyword_boolean_validation():
    assert validate_boolean_expr('Python AND ("machine learning" OR ML)') is None
    assert validate_boolean_expr("Python AND") is not None
    assert validate_boolean_expr("(A OR B") is not None


def test_contradiction_warning():
    c = CriteriaV1(
        titles=[TitleSpec(title="Nurse")],
        work_modes=["on_site"],
        remote_eligibility=RemoteEligibility(anywhere=True),
    )
    codes = {w["code"] for w in validate_criteria(c)}
    assert "contradiction_onsite_remote" in codes


def test_currency_period_normalization():
    assert to_monthly(120_000, "year") == 10_000
    c = CriteriaV1(
        titles=[TitleSpec(title="Engineer")],
        salary=SalaryFilter(min=5000, currency="EUR", period="month"),
    )
    n = normalize_salary(c)
    assert n.salary is not None
    assert n.salary.min_monthly_usd is not None
    assert n.salary.rate_missing is False
    missing = CriteriaV1(
        titles=[TitleSpec(title="Engineer")],
        salary=SalaryFilter(min=100, currency="XYZ", period="month"),
    )
    m = normalize_salary(missing)
    assert m.salary is not None and m.salary.rate_missing is True
