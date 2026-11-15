"""General pack: the neutral base layer for every workspace."""

from __future__ import annotations

from app.industries.schema import (
    AiBrief,
    AnswerKeyPlan,
    CriteriaDefaults,
    FeatureFlags,
    IndustryPack,
    LadderStep,
    MatchingPlan,
    ProfilePlan,
    ResumePlan,
    SafetyPlan,
    SourcePlan,
    UiManifest,
    Visibility,
)

GROUPS: dict[str, tuple[str, ...]] = {
    "role": ("titles", "occupations", "skills", "seniority"),
    "where": ("locations", "work_modes", "remote_eligibility", "visa_sponsorship", "relocation"),
    "when": ("employment_types", "shifts", "posting_max_age_days"),
    "pay": ("salary", "salary_includes"),
    "company": ("companies",),
    "more": ("keywords", "languages", "education", "clearance", "min_match_score", "facets"),
}

STATES: dict[str, Visibility] = {
    "titles": "visible",
    "occupations": "visible",
    "skills": "visible",
    "seniority": "visible",
    "employment_types": "visible",
    "work_modes": "visible",
    "shifts": "collapsed",
    "remote_eligibility": "visible",
    "locations": "visible",
    "visa_sponsorship": "visible",
    "relocation": "visible",
    "salary": "visible",
    "salary_includes": "collapsed",
    "facets": "collapsed",
    "companies": "visible",
    "posting_max_age_days": "collapsed",
    "languages": "collapsed",
    "education": "collapsed",
    "clearance": "collapsed",
    "keywords": "collapsed",
    "min_match_score": "collapsed",
}

STANDARD_LADDER = (
    LadderStep(key="intern", label_key="seniority.intern", maps_to="intern"),
    LadderStep(key="junior", label_key="seniority.junior", maps_to="junior"),
    LadderStep(key="mid", label_key="seniority.mid", maps_to="mid"),
    LadderStep(key="senior", label_key="seniority.senior", maps_to="senior"),
    LadderStep(key="staff", label_key="seniority.staff", maps_to="staff"),
    LadderStep(key="principal", label_key="seniority.principal", maps_to="principal"),
    LadderStep(key="lead", label_key="seniority.lead", maps_to="lead"),
    LadderStep(key="manager", label_key="seniority.manager", maps_to="manager"),
    LadderStep(key="director", label_key="seniority.director", maps_to="director"),
    LadderStep(key="executive", label_key="seniority.executive", maps_to="executive"),
)

GENERAL = IndustryPack(
    key="general",
    version=1,
    label_key="industry.general.label",
    icon="ph:briefcase",
    ui=UiManifest(
        groups=GROUPS,
        states=STATES,
        profile_sections=(
            "experience",
            "projects",
            "skills",
            "certifications",
            "education",
            "languages",
            "documents",
        ),
    ),
    criteria_defaults=CriteriaDefaults(salary_period="month"),
    seniority_ladder=STANDARD_LADDER,
    answer_keys=AnswerKeyPlan(),
    sources=SourcePlan(
        adapters=("career_jsonld", "search_jooble", "search_adzuna"),
        alert_sources=("indeed", "jobstreet", "linkedin"),
    ),
    matching=MatchingPlan(
        weights={
            "title": 0.22,
            "skills": 0.28,
            "seniority": 0.12,
            "salary": 0.12,
            "freshness": 0.08,
            "location": 0.10,
            "semantic": 0.08,
        },
    ),
    profile=ProfilePlan(
        section_order=(
            "experience",
            "projects",
            "skills",
            "certifications",
            "education",
            "languages",
            "documents",
        ),
        gap_actions=("Take a short course or build one small project in {skill}",),
        found_checklist=(
            "Use a real photo and your legal name",
            "Keep titles and dates identical to your resume",
            "Add your city and work authorization",
            "Complete the profile on the boards you actually use",
        ),
        interview_questions=(
            "Walk me through the experience that best fits this role.",
            "Tell me about a difficult problem and what you changed.",
            "What do you want to learn next?",
        ),
    ),
    resume=ResumePlan(template_id="classic"),
    ai=AiBrief(
        brief=(
            "General job search. Use only facts from the career profile. Ask for real evidence "
            "and keep gaps as gaps."
        )
    ),
    safety=SafetyPlan(),
    features=FeatureFlags(
        be_found=True,
        github_links=False,
        coding_practice=False,
        portfolio_images=True,
        photo_resume=False,
        query_sources=True,
    ),
)
