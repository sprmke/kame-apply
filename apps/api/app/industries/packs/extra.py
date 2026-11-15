"""Curated packs for the most common non-tech fields (IND-10, content only)."""

from __future__ import annotations

from app.industries.packs.general import STANDARD_LADDER
from app.industries.schema import (
    AiBrief,
    AnswerKeyPlan,
    CredentialDef,
    CriteriaDefaults,
    Detection,
    FeatureFlags,
    IndustryPack,
    MatchingPlan,
    ProfilePlan,
    ResumePlan,
    RoleFamily,
    SafetyPlan,
    SourcePlan,
    UiManifest,
    Visibility,
)


def _states(**overrides: Visibility) -> dict[str, Visibility]:
    base: dict[str, Visibility] = {
        "remote_eligibility": "hidden",
        "facets": "hidden",
        "salary_includes": "collapsed",
        "companies": "collapsed",
        "education": "collapsed",
        "clearance": "collapsed",
        "posting_max_age_days": "collapsed",
    }
    base.update(overrides)
    return base


def _pack(
    *,
    key: str,
    icon: str,
    keywords: tuple[str, ...],
    families: tuple[tuple[str, tuple[str, ...]], ...],
    credentials: tuple[tuple[str, tuple[str, ...]], ...] = (),
    states: dict[str, Visibility] | None = None,
    brief: str,
    interview: tuple[str, ...],
    found: tuple[str, ...],
    section_titles: dict[str, str] | None = None,
    features: FeatureFlags | None = None,
) -> IndustryPack:
    return IndustryPack(
        key=key,
        version=1,
        label_key=f"industry.{key}.label",
        icon=icon,
        detection=Detection(title_keywords=keywords),
        role_families=tuple(
            RoleFamily(
                key=family_key,
                label_key=f"industry.{key}.family.{family_key}",
                titles=titles,
            )
            for family_key, titles in families
        ),
        ui=UiManifest(states=states or _states()),
        criteria_defaults=CriteriaDefaults(salary_period="month"),
        seniority_ladder=STANDARD_LADDER,
        credentials=tuple(
            CredentialDef(key=cred, label_key=f"credential.{cred}", aliases=aliases)
            for cred, aliases in credentials
        ),
        answer_keys=AnswerKeyPlan(hide=("github_url",)),
        sources=SourcePlan(
            adapters=("career_jsonld", "search_jooble", "search_adzuna"),
            alert_sources=("indeed", "linkedin"),
            employer_tags=(key,),
        ),
        matching=MatchingPlan(
            weights={
                "title": 0.24,
                "skills": 0.20,
                "seniority": 0.12,
                "salary": 0.10,
                "freshness": 0.08,
                "location": 0.16,
                "credentials": 0.10,
            }
        ),
        profile=ProfilePlan(
            section_order=(
                "experience",
                "certifications",
                "skills",
                "projects",
                "education",
                "languages",
                "documents",
            ),
            labels={"projects": "profile.projects.label"},
            interview_questions=interview,
            found_checklist=found,
        ),
        resume=ResumePlan(
            section_order=(
                "summary",
                "certifications",
                "skills",
                "experience",
                "projects",
                "education",
            ),
            section_titles=section_titles or {},
        ),
        ai=AiBrief(brief=brief, vocabulary=keywords[:8]),
        safety=SafetyPlan(),
        features=features
        or FeatureFlags(
            be_found=True,
            github_links=False,
            coding_practice=False,
            portfolio_images=False,
            photo_resume=False,
            query_sources=True,
        ),
    )


HEALTHCARE = _pack(
    key="healthcare",
    icon="ph:first-aid",
    keywords=(
        "nurse",
        "registered nurse",
        "caregiver",
        "nursing",
        "clinical",
        "patient care",
        "midwife",
    ),
    families=(
        ("nursing", ("Registered nurse", "Staff nurse", "ICU nurse", "Emergency nurse")),
        (
            "allied_health",
            ("Physiotherapist", "Radiographer", "Pharmacist", "Medical technologist"),
        ),
        ("care", ("Caregiver", "Nursing assistant", "Home health aide")),
    ),
    credentials=(
        ("rn_license", ("registered nurse license", "nursing license", "rn license")),
        ("bls_cpr", ("bls", "cpr", "basic life support")),
        ("caregiver_cert", ("caregiver certificate", "caregiving nc ii")),
    ),
    states=_states(shifts="visible", relocation="visible", visa_sponsorship="visible"),
    brief=(
        "Healthcare roles. Evidence that matters: license and registration, specialty, unit, "
        "patient load, shift pattern, and certifications with expiry. Do not invent licenses, "
        "clinical numbers, or employers."
    ),
    interview=(
        "Which unit and patient acuity are you strongest in?",
        "Tell me about a clinical judgment call you made.",
        "How do you handle a shift handover or a patient safety concern?",
    ),
    found=(
        "List your license number only where a verified employer form asks for it",
        "Keep registration and BLS/CPR expiry dates current",
        "Use the same unit names as your resume",
    ),
)

ENGINEERING = _pack(
    key="engineering",
    icon="ph:wrench",
    keywords=(
        "civil engineer",
        "mechanical engineer",
        "electrical engineer",
        "structural",
        "site engineer",
        "cad",
    ),
    families=(
        ("civil", ("Civil engineer", "Structural engineer", "Site engineer")),
        ("mechanical", ("Mechanical engineer", "Maintenance engineer", "Design engineer")),
        ("electrical", ("Electrical engineer", "Controls engineer", "Power engineer")),
    ),
    credentials=(
        ("pe_license", ("pe license", "professional engineer")),
        ("ceng", ("ceng", "chartered engineer")),
        ("pmp", ("pmp", "project management professional")),
    ),
    states=_states(relocation="visible", visa_sponsorship="visible"),
    brief=(
        "Engineering roles outside software. Evidence: project type, scale, standards, safety "
        "record, site or plant context, CAD tools, and registration. Never invent a project "
        "value or a license."
    ),
    interview=(
        "Walk me through a project from design to handover.",
        "How do you handle a safety or quality issue on site?",
        "Which standards and tools do you use most?",
    ),
    found=(
        "Keep registration and license status visible",
        "Name the standards you actually used",
        "Add one project scale metric per role",
    ),
)

TRADES = _pack(
    key="trades",
    icon="ph:hammer",
    keywords=("electrician", "plumber", "welder", "mechanic", "technician", "hvac", "carpenter"),
    families=(
        ("electrical", ("Electrician", "Electrical technician", "Solar installer")),
        ("mechanical", ("Plumber", "HVAC technician", "Welder", "Automotive mechanic")),
        ("site", ("Carpenter", "Mason", "Construction worker")),
    ),
    credentials=(
        ("electrician_license", ("electrician license", "electrical license")),
        ("welding_cert", ("welding certificate", "welder certification")),
        ("drivers_license", ("driver's license", "driving license")),
    ),
    states=_states(shifts="visible", relocation="visible", visa_sponsorship="visible"),
    brief=(
        "Skilled trades. Evidence: license or ticket, tools owned, site or workshop type, "
        "safety record, vehicle, and travel radius. Never invent a ticket or a license number."
    ),
    interview=(
        "Which tickets and tools do you bring?",
        "Tell me about a fault you diagnosed and fixed.",
        "How do you keep a site safe?",
    ),
    found=(
        "List tickets and expiry dates",
        "Say which tools and vehicle you own",
        "Add your travel radius",
    ),
)

CUSTOMER_SERVICE = _pack(
    key="customer_service",
    icon="ph:headset",
    keywords=(
        "customer service",
        "call center",
        "bpo",
        "retail",
        "cashier",
        "support agent",
        "sales associate",
    ),
    families=(
        ("retail", ("Retail associate", "Cashier", "Store supervisor")),
        ("contact_center", ("Customer service agent", "Technical support agent", "Team lead")),
    ),
    states=_states(shifts="visible"),
    brief=(
        "Customer service and retail. Evidence: channel, volume, escalation handling, languages, "
        "sales or quality metrics, and shift availability. Never invent a metric."
    ),
    interview=(
        "Tell me about a difficult customer you turned around.",
        "How do you handle a queue or a backlog?",
        "Which channels and systems have you used?",
    ),
    found=("Add languages and shift availability", "Keep quality or sales metrics real"),
)

EDUCATION = _pack(
    key="education",
    icon="ph:student",
    keywords=("teacher", "tutor", "instructor", "lecturer", "education", "curriculum", "school"),
    families=(
        ("school", ("Primary teacher", "Secondary teacher", "Special education teacher")),
        ("early_years", ("Preschool teacher", "Early years educator", "Childcare worker")),
    ),
    credentials=(
        ("teaching_license", ("teaching license", "teacher registration", "qts")),
        ("tefl", ("tefl", "tesol", "celta")),
    ),
    states=_states(),
    brief=(
        "Education roles. Evidence: subject, grade level, curriculum, class size, outcomes, and "
        "license or registration. Never invent a license or a student outcome."
    ),
    interview=(
        "How do you plan a unit for mixed abilities?",
        "Tell me about a student you helped improve.",
        "How do you involve parents or guardians?",
    ),
    found=("Show your subject and grade level", "Keep license and registration visible"),
)

LOGISTICS = _pack(
    key="logistics",
    icon="ph:truck",
    keywords=(
        "driver",
        "delivery",
        "warehouse",
        "logistics",
        "forklift",
        "dispatcher",
        "supply chain",
    ),
    families=(
        ("driving", ("Delivery driver", "Truck driver", "Bus driver")),
        ("warehouse", ("Warehouse associate", "Forklift operator", "Dispatcher")),
    ),
    credentials=(
        ("cdl", ("cdl", "commercial driver's license")),
        ("forklift_cert", ("forklift certificate", "forklift license")),
    ),
    states=_states(shifts="visible", relocation="visible", visa_sponsorship="visible"),
    brief=(
        "Logistics and driving. Evidence: license class, routes, vehicle type, load volume, "
        "safety record, and shift pattern. Never invent a license class."
    ),
    interview=(
        "Which vehicles and routes are you licensed for?",
        "How do you handle a late or damaged delivery?",
        "What does your safety record look like?",
    ),
    found=("List license class and endorsements", "Keep your route experience specific"),
)

FINANCE = _pack(
    key="finance",
    icon="ph:calculator",
    keywords=("accountant", "finance", "auditor", "bookkeeper", "cpa", "financial analyst", "tax"),
    families=(
        ("accounting", ("Accountant", "Auditor", "Bookkeeper", "Tax associate")),
        ("analysis", ("Financial analyst", "FP&A analyst", "Credit analyst")),
    ),
    credentials=(
        ("cpa", ("cpa", "certified public accountant")),
        ("acca", ("acca",)),
        ("cfa", ("cfa", "chartered financial analyst")),
    ),
    states=_states(),
    brief=(
        "Finance and accounting. Evidence: close cycle, systems, audit scope, portfolio size, and "
        "certifications. Never invent a number, client, or certification."
    ),
    interview=(
        "Walk me through a close or audit you ran.",
        "Which systems and controls do you know?",
        "Tell me about a reconciliation issue you found.",
    ),
    found=("Keep certifications current", "Name the systems you actually used"),
)

ADMIN = _pack(
    key="admin",
    icon="ph:clipboard",
    keywords=(
        "administrative assistant",
        "virtual assistant",
        "executive assistant",
        "office manager",
        "data entry",
    ),
    families=(
        ("office", ("Administrative assistant", "Executive assistant", "Office manager")),
        ("virtual", ("Virtual assistant", "Data entry specialist", "Customer support assistant")),
    ),
    states=_states(),
    brief=(
        "Admin and virtual assistance. Evidence: tools, calendar and inbox volume, languages, "
        "response time, and confidentiality. Never invent a client or a volume."
    ),
    interview=(
        "Which tools and calendars do you manage?",
        "How do you handle competing priorities?",
        "How do you protect confidential information?",
    ),
    found=("List the tools you actually use", "State your timezone and language coverage"),
)

SALES_MARKETING = _pack(
    key="sales_marketing",
    icon="ph:chart-line",
    keywords=(
        "sales",
        "account executive",
        "marketing",
        "growth",
        "seo",
        "content",
        "brand",
        "campaign",
    ),
    families=(
        ("sales", ("Account executive", "Sales representative", "Sales manager")),
        (
            "marketing",
            ("Marketing manager", "Content marketer", "Growth marketer", "SEO specialist"),
        ),
    ),
    states=_states(),
    brief=(
        "Sales and marketing. Evidence: quota, pipeline, campaign results, channels, audience, "
        "and tools. Never invent revenue or campaign numbers."
    ),
    interview=(
        "Walk me through a deal or campaign you owned.",
        "How do you qualify or prioritize?",
        "Which channels and tools work for you?",
    ),
    found=("Keep quota and campaign numbers real", "Show the channels you actually ran"),
)

CREATIVE = _pack(
    key="creative",
    icon="ph:palette",
    keywords=(
        "designer",
        "graphic design",
        "ux designer",
        "illustrator",
        "photographer",
        "video editor",
        "content creator",
    ),
    families=(
        ("design", ("Product designer", "Graphic designer", "UX designer", "Illustrator")),
        ("content", ("Photographer", "Video editor", "Content creator")),
    ),
    states=_states(),
    brief=(
        "Creative roles. Evidence: portfolio pieces, tools, audience, and outcomes. Never claim "
        "a project you cannot show or describe."
    ),
    interview=(
        "Walk me through one piece in your portfolio.",
        "How do you take feedback on creative work?",
        "Which tools and formats do you work in?",
    ),
    found=("Link a portfolio you can show", "Name your tools and formats"),
    features=FeatureFlags(
        be_found=True,
        github_links=False,
        coding_practice=False,
        portfolio_images=True,
        photo_resume=False,
        query_sources=True,
    ),
)

EXTRA_PACKS: tuple[IndustryPack, ...] = (
    HEALTHCARE,
    ENGINEERING,
    TRADES,
    CUSTOMER_SERVICE,
    EDUCATION,
    LOGISTICS,
    FINANCE,
    ADMIN,
    SALES_MARKETING,
    CREATIVE,
)
