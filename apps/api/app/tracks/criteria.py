"""CriteriaV1: structured Track search definition (PRD F3).

Empty / omitted fields mean "any". Roles (titles or occupations) are the only soft
requirement at save time; the UI defaults every control to Any.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Seniority = Literal[
    "intern",
    "junior",
    "mid",
    "senior",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "executive",
]
EmploymentType = Literal[
    "full_time",
    "part_time",
    "contract",
    "freelance",
    "internship",
    "temporary",
]
WorkMode = Literal["remote", "hybrid", "on_site"]
SalaryPeriod = Literal["hour", "day", "month", "year"]
CompanySize = Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001+"]
CompanyStage = Literal[
    "bootstrapped",
    "seed",
    "series_a",
    "series_b",
    "series_c_plus",
    "public",
    "nonprofit",
    "government",
]


class TitleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    synonyms: list[str] = Field(default_factory=list)
    exclude: bool = False


class OccupationRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    scheme: Literal["esco", "onet", "isco", "soc"] = "esco"
    label: str | None = Field(default=None, max_length=300)


class SkillSets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    must: list[str] = Field(default_factory=list)
    nice: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class RemoteEligibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anywhere: bool = False
    regions: list[str] = Field(default_factory=list)  # APAC, EU, LATAM, ...
    countries: list[str] = Field(default_factory=list)  # ISO-3166-1 alpha-2
    timezone_overlap_hours: int | None = Field(default=None, ge=0, le=24)
    base_tz: str | None = Field(default=None, max_length=64)


class LocationFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    place: str = Field(min_length=1, max_length=200)
    radius_km: int | None = Field(default=None, ge=1, le=500)
    lat: float | None = None
    lon: float | None = None
    country: str | None = Field(default=None, max_length=2)


class SalaryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: float | None = Field(default=None, ge=0)
    max: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    period: SalaryPeriod = "month"
    hide_unspecified: bool = False
    # Filled by currency normalizer; excluded from filters when rate missing.
    min_monthly_usd: float | None = None
    max_monthly_usd: float | None = None
    rate_missing: bool = False


class CompanyFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    sizes: list[CompanySize] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    stages: list[CompanyStage] = Field(default_factory=list)
    exclude_agencies: bool = False


class KeywordFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_expr: str | None = Field(default=None, max_length=2000)
    exclude_expr: str | None = Field(default=None, max_length=2000)


class CapsFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    per_day: int | None = Field(default=None, ge=1, le=500)
    per_company: int | None = Field(default=None, ge=1, le=50)


class CriteriaV1(BaseModel):
    """Source of truth for a Track's search. Version field is on track_criteria, not here."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    titles: list[TitleSpec] = Field(default_factory=list)
    occupations: list[OccupationRef] = Field(default_factory=list)
    skills: SkillSets = Field(default_factory=SkillSets)
    seniority: list[Seniority] = Field(default_factory=list)
    employment_types: list[EmploymentType] = Field(default_factory=list)
    work_modes: list[WorkMode] = Field(default_factory=list)
    remote_eligibility: RemoteEligibility = Field(default_factory=RemoteEligibility)
    locations: list[LocationFilter] = Field(default_factory=list)
    visa_sponsorship: bool | None = None
    relocation: bool | None = None
    salary: SalaryFilter | None = None
    companies: CompanyFilter = Field(default_factory=CompanyFilter)
    posting_max_age_days: int | None = Field(default=None, ge=1, le=365)
    languages: list[str] = Field(default_factory=list)
    education: str | None = Field(default=None, max_length=200)
    clearance: str | None = Field(default=None, max_length=120)
    keywords: KeywordFilter = Field(default_factory=KeywordFilter)
    min_match_score: int | None = Field(default=None, ge=0, le=100)
    caps: CapsFilter = Field(default_factory=CapsFilter)

    @field_validator("languages")
    @classmethod
    def _lang_codes(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for item in v:
            code = item.strip().lower()
            if not code or len(code) > 16:
                raise ValueError("invalid language code")
            out.append(code)
        return out

    def has_role_signal(self) -> bool:
        include_titles = [t for t in self.titles if not t.exclude]
        return bool(include_titles or self.occupations)

    def model_dump_stored(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def empty_criteria() -> CriteriaV1:
    return CriteriaV1()


def criteria_from_dict(data: dict[str, Any] | None) -> CriteriaV1:
    if not data:
        return empty_criteria()
    return CriteriaV1.model_validate(data)
