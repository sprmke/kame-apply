"""Curated taxonomy + 40+ track templates for local/CI. Full ESCO/O*NET via refresh script."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy import models as m
from app.taxonomy.aliases import SKILL_ALIASES
from app.tracks.currency import FALLBACK_USD_PER_UNIT, rates_payload

# Compact ESCO-like occupations for tests and first-run UX.
OCCUPATIONS: list[dict[str, Any]] = [
    {
        "scheme": "esco",
        "code": "2512.1",
        "label": "Software developer",
        "isco_code": "2512",
        "alt_titles": ["Software engineer", "Programmer", "Desarrollador"],
    },
    {
        "scheme": "esco",
        "code": "2511.1",
        "label": "Systems analyst",
        "isco_code": "2511",
        "alt_titles": ["IT analyst"],
    },
    {
        "scheme": "esco",
        "code": "2514.1",
        "label": "Applications programmer",
        "isco_code": "2514",
        "alt_titles": ["Backend engineer", "Frontend engineer", "Full stack engineer"],
    },
    {
        "scheme": "esco",
        "code": "2523.1",
        "label": "Computer network professional",
        "isco_code": "2523",
        "alt_titles": ["Network engineer", "DevOps engineer", "SRE"],
    },
    {
        "scheme": "esco",
        "code": "2511.15",
        "label": "Data scientist",
        "isco_code": "2511",
        "alt_titles": ["ML engineer", "Machine learning engineer"],
    },
    {
        "scheme": "esco",
        "code": "1330.1",
        "label": "ICT service manager",
        "isco_code": "1330",
        "alt_titles": ["Engineering manager", "Product engineering manager"],
    },
    {
        "scheme": "esco",
        "code": "2431.1",
        "label": "Advertising and marketing specialist",
        "isco_code": "2431",
        "alt_titles": ["Product marketing manager", "Growth marketer"],
    },
    {
        "scheme": "esco",
        "code": "1221.1",
        "label": "Sales and marketing manager",
        "isco_code": "1221",
        "alt_titles": ["Product manager", "Product owner"],
    },
    {
        "scheme": "esco",
        "code": "2166.1",
        "label": "Graphic and multimedia designer",
        "isco_code": "2166",
        "alt_titles": ["Product designer", "UX designer", "UI designer"],
    },
    {
        "scheme": "esco",
        "code": "2221.1",
        "label": "Nursing professional",
        "isco_code": "2221",
        "alt_titles": ["Registered nurse", "ICU nurse", "Staff nurse"],
    },
    {
        "scheme": "esco",
        "code": "2211.1",
        "label": "Generalist medical practitioner",
        "isco_code": "2211",
        "alt_titles": ["Physician", "GP"],
    },
    {
        "scheme": "esco",
        "code": "2262.1",
        "label": "Pharmacist",
        "isco_code": "2262",
        "alt_titles": ["Clinical pharmacist"],
    },
    {
        "scheme": "esco",
        "code": "2330.1",
        "label": "Secondary education teacher",
        "isco_code": "2330",
        "alt_titles": ["High school teacher"],
    },
    {
        "scheme": "esco",
        "code": "2341.1",
        "label": "Primary school teacher",
        "isco_code": "2341",
        "alt_titles": ["Elementary teacher"],
    },
    {
        "scheme": "esco",
        "code": "2411.1",
        "label": "Accountant",
        "isco_code": "2411",
        "alt_titles": ["Financial accountant", "Auditor"],
    },
    {
        "scheme": "esco",
        "code": "2611.1",
        "label": "Lawyer",
        "isco_code": "2611",
        "alt_titles": ["Attorney", "Solicitor"],
    },
    {
        "scheme": "esco",
        "code": "3434.1",
        "label": "Chef",
        "isco_code": "3434",
        "alt_titles": ["Cook", "Sous chef"],
    },
    {
        "scheme": "esco",
        "code": "7231.1",
        "label": "Motor vehicle mechanic",
        "isco_code": "7231",
        "alt_titles": ["Auto mechanic"],
    },
    {
        "scheme": "onet",
        "code": "15-1252.00",
        "label": "Software Developers",
        "isco_code": "2512",
        "alt_titles": ["Application developer", "Systems software developer"],
    },
    {
        "scheme": "onet",
        "code": "29-1141.00",
        "label": "Registered Nurses",
        "isco_code": "2221",
        "alt_titles": ["RN", "Staff RN"],
    },
    {
        "scheme": "onet",
        "code": "15-2051.00",
        "label": "Data Scientists",
        "isco_code": "2511",
        "alt_titles": ["Data science specialist"],
    },
    {
        "scheme": "onet",
        "code": "11-2021.00",
        "label": "Marketing Managers",
        "isco_code": "1221",
        "alt_titles": ["Brand manager"],
    },
    {
        "scheme": "onet",
        "code": "15-1212.00",
        "label": "Information Security Analysts",
        "isco_code": "2529",
        "alt_titles": ["Security engineer", "Cybersecurity analyst"],
    },
    {
        "scheme": "onet",
        "code": "17-2141.00",
        "label": "Mechanical Engineers",
        "isco_code": "2144",
        "alt_titles": ["Mechanical design engineer"],
    },
]

SKILLS: list[dict[str, Any]] = [
    {"scheme": "esco", "code": "JS", "label": "JavaScript", "aliases": ["JS", "Javascript"]},
    {"scheme": "esco", "code": "TS", "label": "TypeScript", "aliases": ["TS"]},
    {"scheme": "esco", "code": "PY", "label": "Python", "aliases": ["Py"]},
    {"scheme": "esco", "code": "JAVA", "label": "Java", "aliases": []},
    {"scheme": "esco", "code": "GO", "label": "Go", "aliases": ["Golang"]},
    {"scheme": "esco", "code": "K8S", "label": "Kubernetes", "aliases": ["K8s", "k8s"]},
    {"scheme": "esco", "code": "DOCKER", "label": "Docker", "aliases": []},
    {"scheme": "esco", "code": "PG", "label": "PostgreSQL", "aliases": ["Postgres", "psql"]},
    {"scheme": "esco", "code": "REACT", "label": "React", "aliases": ["React.js", "ReactJS"]},
    {"scheme": "esco", "code": "VUE", "label": "Vue", "aliases": ["Vue.js", "VueJS"]},
    {"scheme": "esco", "code": "NODE", "label": "Node.js", "aliases": ["Node", "nodejs"]},
    {"scheme": "esco", "code": "TF", "label": "Terraform", "aliases": ["TF"]},
    {"scheme": "esco", "code": "AWS", "label": "Amazon Web Services", "aliases": ["AWS"]},
    {"scheme": "esco", "code": "ML", "label": "Machine Learning", "aliases": ["ML"]},
    {"scheme": "esco", "code": "SQL", "label": "SQL", "aliases": []},
    {"scheme": "esco", "code": "FIGMA", "label": "Figma", "aliases": []},
    {"scheme": "esco", "code": "NURSING", "label": "Patient care", "aliases": ["Nursing care"]},
    {"scheme": "esco", "code": "ICU", "label": "Intensive care", "aliases": ["ICU"]},
    {"scheme": "esco", "code": "ACCTG", "label": "Financial reporting", "aliases": ["IFRS"]},
    {"scheme": "onet", "code": "2.C.3.a", "label": "English language", "aliases": ["English"]},
]


def _templates() -> list[dict[str, Any]]:
    """40+ starter templates across industries."""
    base: list[tuple[str, str, str, str, list[str], int]] = [
        # slug, name, industry, nl, must_skills, hue
        (
            "software-engineer",
            "Software Engineer",
            "technology",
            "Software engineer, remote-friendly, full-time",
            ["Python", "SQL"],
            1,
        ),
        (
            "ai-engineer",
            "AI Engineer",
            "technology",
            "AI engineer focused on LLMs and Python, remote worldwide",
            ["Python", "Machine Learning"],
            2,
        ),
        (
            "frontend-engineer",
            "Frontend Engineer",
            "technology",
            "Frontend engineer with TypeScript and Vue or React",
            ["TypeScript", "Vue"],
            3,
        ),
        (
            "backend-engineer",
            "Backend Engineer",
            "technology",
            "Backend engineer, Go or Python, PostgreSQL",
            ["PostgreSQL", "Go"],
            4,
        ),
        (
            "fullstack-engineer",
            "Full-Stack Engineer",
            "technology",
            "Full-stack engineer, TypeScript, Node.js",
            ["TypeScript", "Node.js"],
            5,
        ),
        (
            "devops-engineer",
            "DevOps / SRE",
            "technology",
            "DevOps or SRE, Kubernetes, Terraform, AWS",
            ["Kubernetes", "Terraform"],
            6,
        ),
        (
            "data-scientist",
            "Data Scientist",
            "technology",
            "Data scientist, Python, SQL, machine learning",
            ["Python", "Machine Learning"],
            7,
        ),
        (
            "security-engineer",
            "Security Engineer",
            "technology",
            "Security engineer, cloud and application security",
            ["Amazon Web Services"],
            8,
        ),
        (
            "mobile-engineer",
            "Mobile Engineer",
            "technology",
            "Mobile engineer, iOS or Android",
            [],
            1,
        ),
        ("qa-engineer", "QA Engineer", "technology", "QA engineer, automation preferred", [], 2),
        ("product-manager", "Product Manager", "product", "Product manager for B2B SaaS", [], 3),
        (
            "product-designer",
            "Product Designer",
            "design",
            "Product designer, Figma, UX research",
            ["Figma"],
            4,
        ),
        (
            "ux-researcher",
            "UX Researcher",
            "design",
            "UX researcher, qualitative and quantitative",
            [],
            5,
        ),
        (
            "engineering-manager",
            "Engineering Manager",
            "technology",
            "Engineering manager for a platform team",
            [],
            6,
        ),
        (
            "data-analyst",
            "Data Analyst",
            "technology",
            "Data analyst, SQL and dashboards",
            ["SQL"],
            7,
        ),
        (
            "registered-nurse",
            "Registered Nurse",
            "healthcare",
            "Registered nurse, hospital setting",
            ["Patient care"],
            8,
        ),
        (
            "icu-nurse-uae",
            "ICU Nurse - UAE / Saudi",
            "healthcare",
            "ICU nurse, night shifts, UAE or Saudi, visa sponsorship",
            ["Intensive care", "Patient care"],
            1,
        ),
        ("pharmacist", "Pharmacist", "healthcare", "Pharmacist, community or hospital", [], 2),
        ("physician", "Physician", "healthcare", "General practice physician", [], 3),
        ("teacher-secondary", "Secondary Teacher", "education", "Secondary school teacher", [], 4),
        ("teacher-primary", "Primary Teacher", "education", "Primary school teacher", [], 5),
        (
            "accountant",
            "Accountant",
            "finance",
            "Accountant, financial reporting",
            ["Financial reporting"],
            6,
        ),
        ("financial-analyst", "Financial Analyst", "finance", "Financial analyst, modeling", [], 7),
        ("lawyer", "Lawyer", "legal", "Lawyer, corporate or litigation", [], 8),
        ("paralegal", "Paralegal", "legal", "Paralegal, document review", [], 1),
        ("chef", "Chef", "hospitality", "Chef, restaurant kitchen", [], 2),
        ("hotel-manager", "Hotel Manager", "hospitality", "Hotel or resort manager", [], 3),
        ("mechanic", "Vehicle Mechanic", "trades", "Motor vehicle mechanic", [], 4),
        ("electrician", "Electrician", "trades", "Licensed electrician", [], 5),
        (
            "civil-engineer",
            "Civil Engineer",
            "engineering",
            "Civil engineer, infrastructure projects",
            [],
            6,
        ),
        (
            "mechanical-engineer",
            "Mechanical Engineer",
            "engineering",
            "Mechanical engineer, product design",
            [],
            7,
        ),
        (
            "marketing-manager",
            "Marketing Manager",
            "marketing",
            "Marketing manager, B2B or B2C",
            [],
            8,
        ),
        (
            "content-marketer",
            "Content Marketer",
            "marketing",
            "Content marketer, SEO writing",
            [],
            1,
        ),
        ("sales-ae", "Account Executive", "sales", "Account executive, SaaS sales", [], 2),
        (
            "customer-success",
            "Customer Success Manager",
            "sales",
            "Customer success manager",
            [],
            3,
        ),
        ("hr-generalist", "HR Generalist", "people", "HR generalist, full cycle", [], 4),
        ("recruiter", "Recruiter", "people", "Technical recruiter", [], 5),
        ("operations-manager", "Operations Manager", "operations", "Operations manager", [], 6),
        ("supply-chain", "Supply Chain Analyst", "operations", "Supply chain analyst", [], 7),
        (
            "research-scientist",
            "Research Scientist",
            "science",
            "Research scientist, lab or computational",
            [],
            8,
        ),
        ("biotech-associate", "Biotech Associate", "science", "Biotech research associate", [], 1),
        ("policy-analyst", "Policy Analyst", "public", "Policy analyst, government or NGO", [], 2),
        (
            "project-manager",
            "Project Manager",
            "operations",
            "Project manager, PMP preferred",
            [],
            3,
        ),
        ("scrum-master", "Scrum Master", "technology", "Scrum master / agile coach", [], 4),
    ]
    out: list[dict[str, Any]] = []
    for i, (slug, name, industry, nl, must, hue) in enumerate(base):
        titles = [{"title": name, "synonyms": [], "exclude": False}]
        criteria: dict[str, Any] = {
            "schema_version": 1,
            "titles": titles,
            "skills": {"must": must, "nice": [], "exclude": []},
        }
        if "visa" in nl.lower():
            criteria["visa_sponsorship"] = True
        if "uae" in nl.lower() or "saudi" in nl.lower():
            criteria["remote_eligibility"] = {
                "anywhere": False,
                "regions": ["MENA"],
                "countries": ["AE", "SA"],
                "timezone_overlap_hours": None,
                "base_tz": None,
            }
            criteria["work_modes"] = ["on_site", "hybrid"]
        if "remote" in nl.lower():
            criteria["work_modes"] = ["remote", "hybrid"]
            criteria["remote_eligibility"] = {
                "anywhere": "worldwide" in nl.lower(),
                "regions": [],
                "countries": [],
                "timezone_overlap_hours": None,
                "base_tz": None,
            }
        out.append(
            {
                "slug": slug,
                "name": name,
                "industry": industry,
                "description": nl,
                "icon": "ph:path",
                "color_hue": hue,
                "criteria": criteria,
                "nl_seed": nl,
                "sort_order": i + 1,
            }
        )
    return out


async def seed_taxonomy(session: AsyncSession) -> dict[str, int]:
    """Idempotent upsert of curated occupations, skills, aliases, templates, FX fallback."""
    occ_count = skill_count = alias_count = tmpl_count = 0

    for row in OCCUPATIONS:
        stmt = (
            pg_insert(m.TaxonomyOccupation)
            .values(
                scheme=row["scheme"],
                code=row["code"],
                label=row["label"],
                isco_code=row.get("isco_code"),
                alt_titles=row.get("alt_titles") or [],
                labels={"en": row["label"]},
            )
            .on_conflict_do_nothing(constraint="uq_taxonomy_occupations_scheme_code")
        )
        result = await session.execute(stmt)
        occ_count += int(getattr(result, "rowcount", 0) or 0)

    skill_ids: dict[str, Any] = {}
    for row in SKILLS:
        stmt = (
            pg_insert(m.TaxonomySkill)
            .values(
                scheme=row["scheme"],
                code=row["code"],
                label=row["label"],
                aliases=row.get("aliases") or [],
                labels={"en": row["label"]},
            )
            .on_conflict_do_nothing(constraint="uq_taxonomy_skills_scheme_code")
        )
        await session.execute(stmt)
        existing = (
            await session.execute(
                select(m.TaxonomySkill).where(
                    m.TaxonomySkill.scheme == row["scheme"],
                    m.TaxonomySkill.code == row["code"],
                )
            )
        ).scalar_one()
        skill_ids[row["label"].casefold()] = existing.id
        skill_count += 1
        for alias in row.get("aliases") or []:
            a_stmt = (
                pg_insert(m.TaxonomyAlias)
                .values(
                    kind="skill",
                    alias=alias,
                    alias_key=alias.casefold(),
                    canonical=row["label"],
                    skill_id=existing.id,
                )
                .on_conflict_do_nothing(constraint="uq_taxonomy_aliases_kind_key")
            )
            ar = await session.execute(a_stmt)
            alias_count += int(getattr(ar, "rowcount", 0) or 0)

    for alias, canonical in SKILL_ALIASES.items():
        sid = skill_ids.get(canonical.casefold())
        a_stmt = (
            pg_insert(m.TaxonomyAlias)
            .values(
                kind="skill",
                alias=alias,
                alias_key=alias,
                canonical=canonical,
                skill_id=sid,
            )
            .on_conflict_do_nothing(constraint="uq_taxonomy_aliases_kind_key")
        )
        ar = await session.execute(a_stmt)
        alias_count += int(getattr(ar, "rowcount", 0) or 0)

    # ESCO ↔ O*NET crosswalk samples
    crosswalks = [
        ("esco", "2512.1", "onet", "15-1252.00"),
        ("esco", "2221.1", "onet", "29-1141.00"),
        ("esco", "2511.15", "onet", "15-2051.00"),
    ]
    for fs, fc, ts, tc in crosswalks:
        await session.execute(
            pg_insert(m.TaxonomyCrosswalk)
            .values(from_scheme=fs, from_code=fc, to_scheme=ts, to_code=tc, confidence="exact")
            .on_conflict_do_nothing(constraint="uq_taxonomy_crosswalk")
        )

    for tmpl in _templates():
        stmt = (
            pg_insert(m.TrackTemplate)
            .values(**tmpl)
            .on_conflict_do_nothing(constraint="uq_track_templates_slug")
        )
        tr = await session.execute(stmt)
        tmpl_count += int(getattr(tr, "rowcount", 0) or 0)

    rates = rates_payload()
    rates["rates"] = dict(FALLBACK_USD_PER_UNIT)
    await session.execute(
        pg_insert(m.CurrencyRate).values(
            as_of=rates["as_of"],
            base=rates["base"],
            rates=rates["rates"],
            source=rates["source"],
        )
    )

    await session.commit()
    return {
        "occupations_inserted": occ_count,
        "skills": skill_count,
        "aliases_inserted": alias_count,
        "templates_inserted": tmpl_count,
        "template_total": len(_templates()),
    }
