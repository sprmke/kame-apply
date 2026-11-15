"""Named skills and tools, for inline match highlighting.

Only concrete, named things live here: languages, frameworks, platforms, tools,
databases, and products. Soft skills and generic practices stay out because they
match ordinary prose and the qualification ledger already covers them.

The list is deliberately small and curated. It is not a taxonomy replacement;
`app.taxonomy.seed` still owns the stored skill catalogue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.taxonomy.aliases import skill_key


@dataclass(frozen=True, slots=True)
class SkillTerm:
    label: str
    aliases: tuple[str, ...] = ()
    # Common English words that double as product or language names.
    case_sensitive: bool = False
    # Phrases that turn the surface into ordinary prose ("Excel at", "Go to").
    blocked_after: tuple[str, ...] = ()

    @property
    def surfaces(self) -> tuple[str, ...]:
        return (self.label, *self.aliases)


SKILL_TERMS: tuple[SkillTerm, ...] = (
    # Languages
    SkillTerm("JavaScript", ("JS",)),
    SkillTerm("TypeScript", ("TS",)),
    SkillTerm("Python"),
    SkillTerm("Java"),
    SkillTerm("Kotlin"),
    SkillTerm("Swift", case_sensitive=True),
    SkillTerm("Go", ("Golang",), case_sensitive=True, blocked_after=("to", "back", "ahead")),
    SkillTerm("Rust"),
    SkillTerm("Ruby"),
    SkillTerm("PHP"),
    SkillTerm("C#", ("CSharp",)),
    SkillTerm("C++", ("CPP",)),
    SkillTerm(".NET", ("ASP.NET", "dotnet")),
    SkillTerm("Scala"),
    SkillTerm("Elixir"),
    SkillTerm("Haskell"),
    SkillTerm("Objective-C", ("Objective C",)),
    SkillTerm("Bash"),
    SkillTerm("SQL", case_sensitive=True),
    SkillTerm("NoSQL"),
    # Web
    SkillTerm("HTML"),
    SkillTerm("CSS"),
    SkillTerm(
        "React",
        ("React.js", "ReactJS", "React JS"),
        case_sensitive=True,
        blocked_after=("to",),
    ),
    SkillTerm("React Native"),
    SkillTerm("Next.js", ("NextJS", "Next JS")),
    SkillTerm("Vue", ("Vue.js", "VueJS")),
    SkillTerm("Nuxt", ("Nuxt.js",)),
    SkillTerm("Angular"),
    SkillTerm("Svelte", ("SvelteKit",)),
    SkillTerm("Astro"),
    SkillTerm("Remix"),
    SkillTerm("Gatsby"),
    SkillTerm("Node.js", ("NodeJS", "Node JS", "Node")),
    SkillTerm("Express.js", ("ExpressJS", "Express")),
    SkillTerm("NestJS", ("Nest.js",)),
    SkillTerm("Django"),
    SkillTerm("Flask"),
    SkillTerm("FastAPI"),
    SkillTerm("Laravel"),
    SkillTerm("Ruby on Rails", ("Rails",)),
    SkillTerm("Spring Boot", ("Spring Framework",)),
    SkillTerm("Tailwind CSS", ("Tailwind",)),
    SkillTerm("Sass", ("SCSS",)),
    SkillTerm("GraphQL"),
    SkillTerm("REST", ("REST API", "RESTful"), case_sensitive=True),
    SkillTerm("gRPC"),
    SkillTerm("WebSockets", ("WebSocket",)),
    SkillTerm("Microservices"),
    SkillTerm("Webpack"),
    SkillTerm("Vite"),
    SkillTerm("Flutter"),
    SkillTerm("Ionic"),
    SkillTerm("SwiftUI"),
    SkillTerm("Jetpack Compose"),
    # Data and AI
    SkillTerm("Machine Learning", ("ML",)),
    SkillTerm("Deep Learning"),
    SkillTerm("Natural Language Processing", ("NLP",)),
    SkillTerm("LLM", ("LLMs",)),
    SkillTerm("PyTorch"),
    SkillTerm("TensorFlow"),
    SkillTerm("scikit-learn", ("sklearn", "Scikit Learn")),
    SkillTerm("Keras"),
    SkillTerm("Pandas"),
    SkillTerm("NumPy"),
    SkillTerm("Hugging Face", ("HuggingFace",)),
    SkillTerm("LangChain"),
    SkillTerm("Apache Spark", ("Spark",), case_sensitive=True),
    SkillTerm("Apache Airflow", ("Airflow",)),
    SkillTerm("dbt"),
    SkillTerm("Snowflake"),
    SkillTerm("Databricks"),
    SkillTerm("BigQuery"),
    SkillTerm("Redshift"),
    SkillTerm("Tableau"),
    SkillTerm("Power BI", ("PowerBI",)),
    SkillTerm("Looker"),
    SkillTerm("Metabase"),
    SkillTerm("Excel", case_sensitive=True, blocked_after=("at", "in")),
    SkillTerm("Google Sheets"),
    # Databases and infrastructure
    SkillTerm("PostgreSQL", ("Postgres", "psql")),
    SkillTerm("MySQL"),
    SkillTerm("MongoDB", ("Mongo",)),
    SkillTerm("Redis"),
    SkillTerm("Elasticsearch"),
    SkillTerm("DynamoDB"),
    SkillTerm("Cassandra"),
    SkillTerm("Kafka"),
    SkillTerm("RabbitMQ"),
    SkillTerm("Docker"),
    SkillTerm("Kubernetes", ("K8s",)),
    SkillTerm("Terraform"),
    SkillTerm("Ansible"),
    SkillTerm("Pulumi"),
    SkillTerm("AWS", ("Amazon Web Services",)),
    SkillTerm("GCP", ("Google Cloud", "Google Cloud Platform")),
    SkillTerm("Azure", ("Microsoft Azure",)),
    SkillTerm("CI/CD", ("CICD", "Continuous Integration")),
    SkillTerm("Jenkins"),
    SkillTerm("GitHub Actions"),
    SkillTerm("GitLab CI", ("GitLab",)),
    SkillTerm("CircleCI"),
    SkillTerm("Linux"),
    SkillTerm("Git"),
    SkillTerm("Nginx"),
    SkillTerm("Serverless"),
    SkillTerm("Salesforce", case_sensitive=True),
    SkillTerm("ServiceNow"),
    SkillTerm("Workday", case_sensitive=True),
    SkillTerm("SAP", case_sensitive=True),
    SkillTerm("Oracle", case_sensitive=True),
    SkillTerm("NetSuite"),
    SkillTerm("QuickBooks"),
    SkillTerm("Xero"),
    SkillTerm("HubSpot"),
    SkillTerm("Shopify"),
    SkillTerm("Stripe", case_sensitive=True),
    SkillTerm("Twilio"),
    SkillTerm("Segment", case_sensitive=True),
    SkillTerm("Zendesk"),
    SkillTerm("Intercom"),
    SkillTerm("Freshdesk"),
    SkillTerm("Jira"),
    SkillTerm("Confluence"),
    SkillTerm("Notion", case_sensitive=True),
    SkillTerm("Asana"),
    SkillTerm("Trello"),
    SkillTerm("Monday.com"),
    SkillTerm("Slack", case_sensitive=True, blocked_after=("off",)),
    SkillTerm("Zoom"),
    SkillTerm("Google Analytics", ("GA4",)),
    SkillTerm("Google Ads", ("Google AdWords",)),
    SkillTerm("Meta Ads", ("Facebook Ads",)),
    SkillTerm("Mailchimp"),
    SkillTerm("Klaviyo"),
    SkillTerm("SEO"),
    SkillTerm("SEM"),
    SkillTerm("WordPress"),
    SkillTerm("Webflow"),
    SkillTerm("Contentful"),
    # Design
    SkillTerm("Figma"),
    SkillTerm("Sketch", case_sensitive=True),
    SkillTerm("Adobe XD"),
    SkillTerm("Photoshop"),
    SkillTerm("Illustrator"),
    SkillTerm("InDesign"),
    SkillTerm("Framer"),
    SkillTerm("UX", case_sensitive=True),
    SkillTerm("UI", case_sensitive=True),
    SkillTerm("WCAG"),
    SkillTerm("Design Systems", ("Design System",)),
    # Testing
    SkillTerm("Jest"),
    SkillTerm("Vitest"),
    SkillTerm("Cypress"),
    SkillTerm("Playwright"),
    SkillTerm("Selenium"),
    SkillTerm("PyTest"),
    SkillTerm("JUnit"),
    # Healthcare, finance, and office tools
    SkillTerm("Epic", case_sensitive=True),
    SkillTerm("Cerner"),
    SkillTerm("MEDITECH", ("Meditech",)),
    SkillTerm("EHR", case_sensitive=True),
    SkillTerm("EMR", case_sensitive=True),
    SkillTerm("HIPAA", case_sensitive=True),
    SkillTerm("BLS", case_sensitive=True),
    SkillTerm("ACLS", case_sensitive=True),
    SkillTerm("PALS", case_sensitive=True),
    SkillTerm("Phlebotomy"),
    SkillTerm("ICD-10", ("ICD10",)),
    SkillTerm("CPT", case_sensitive=True),
    SkillTerm("GAAP", case_sensitive=True),
    SkillTerm("IFRS", case_sensitive=True),
    SkillTerm("SOX", case_sensitive=True),
    SkillTerm("AutoCAD"),
    SkillTerm("SolidWorks"),
    SkillTerm("Revit"),
    SkillTerm("ADP", case_sensitive=True),
    SkillTerm("SuccessFactors"),
    SkillTerm("PowerPoint", ("Power Point",)),
    SkillTerm("Outlook", case_sensitive=True),
    SkillTerm("Microsoft 365", ("Office 365", "Microsoft Office")),
    SkillTerm("Google Workspace", ("G Suite",)),
)


@dataclass(slots=True)
class SkillHit:
    label: str
    variants: list[str] = field(default_factory=list)
    mentions: int = 0
    required_mentions: int = 0
    case_sensitive: bool = False


def _boundary(surface: str, blocked_after: tuple[str, ...] = ()) -> str:
    tail = "".join(rf"(?!\s+{re.escape(word)}\b)" for word in blocked_after)
    return rf"(?<![A-Za-z0-9_]){re.escape(surface)}(?![A-Za-z0-9_]){tail}"


def count_surface(
    text: str,
    surface: str,
    *,
    case_sensitive: bool = False,
    blocked_after: tuple[str, ...] = (),
) -> int:
    """Count whole-word occurrences of one surface form."""
    if not text or not surface:
        return 0
    flags = 0 if case_sensitive else re.IGNORECASE
    return sum(1 for _ in re.finditer(_boundary(surface, blocked_after), text, flags))


@dataclass(frozen=True, slots=True)
class _Surface:
    term: SkillTerm
    surface: str
    pattern: re.Pattern[str]


def _surfaces() -> list[_Surface]:
    out: list[_Surface] = []
    seen: set[str] = set()
    for term in SKILL_TERMS:
        flags = 0 if term.case_sensitive else re.IGNORECASE
        for surface in term.surfaces:
            key = surface.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(
                _Surface(
                    term,
                    surface,
                    re.compile(_boundary(surface, term.blocked_after), flags),
                )
            )
    return out


_SURFACES: tuple[_Surface, ...] = tuple(_surfaces())

# Requirement language near a mention. Used only to rank gaps: a term the posting
# asks for should survive the summary cap before an incidental mention does.
_REQUIREMENT = re.compile(
    r"\b(?:required|requires?|must|essential|proficien\w*|expertise|"
    r"experience (?:with|in)|knowledge of|familiar\w*|years?)\b",
    re.IGNORECASE,
)

# Canonical key (see skill_key) to display label. Includes aliases so a profile
# skill spelled "Postgres" resolves to the "PostgreSQL" term.
_LABEL_BY_KEY: dict[str, str] = {}
for _term in SKILL_TERMS:
    for _surface in _term.surfaces:
        _LABEL_BY_KEY.setdefault(skill_key(_surface), _term.label)

_TERM_BY_LABEL: dict[str, SkillTerm] = {term.label: term for term in SKILL_TERMS}


def canonical_skill_label(name: str) -> str:
    """Resolve a spelling variant to the display label; return the name unchanged otherwise."""
    clean = (name or "").strip()
    if not clean:
        return ""
    return _LABEL_BY_KEY.get(skill_key(clean), clean)


def skill_case_sensitive(name: str) -> bool:
    """True when the canonical term is a common word and only matches in its exact casing."""
    label = canonical_skill_label(name)
    return _TERM_BY_LABEL[label].case_sensitive if label in _TERM_BY_LABEL else False


def skill_blocked_after(name: str) -> tuple[str, ...]:
    """Phrases that make the surface read as ordinary prose rather than the named skill."""
    label = canonical_skill_label(name)
    return _TERM_BY_LABEL[label].blocked_after if label in _TERM_BY_LABEL else ()


def skill_surfaces(name: str) -> tuple[str, ...]:
    label = canonical_skill_label(name)
    if label in _TERM_BY_LABEL:
        return _TERM_BY_LABEL[label].surfaces
    return (name,) if name else ()


def find_skill_terms(text: str, *, limit: int = 50_000) -> list[SkillHit]:
    """Find named skills in visible posting text. Case and word boundaries respected."""
    body = (text or "")[:limit]
    if not body:
        return []

    hits: dict[str, SkillHit] = {}
    variants: dict[str, list[str]] = {}
    seen_variants: dict[str, set[str]] = {}
    folded = body.casefold()

    for info in _SURFACES:
        # Cheap substring gate: most of the vocabulary is absent from any one posting.
        if info.surface.casefold() not in folded:
            continue
        term = info.term
        label = term.label
        for match in info.pattern.finditer(body):
            hit = hits.get(label)
            if hit is None:
                hit = SkillHit(label=label, case_sensitive=term.case_sensitive)
                hits[label] = hit
                variants[label] = []
                seen_variants[label] = set()
            hit.mentions += 1
            found = match.group(0)
            key = found.casefold()
            if key not in seen_variants[label] and len(variants[label]) < 4:
                seen_variants[label].add(key)
                variants[label].append(info.surface)
                hit.variants = variants[label]
            context = body[max(0, match.start() - 120) : match.end() + 120]
            if _REQUIREMENT.search(context):
                hit.required_mentions += 1

    return sorted(hits.values(), key=lambda hit: hit.label.casefold())
