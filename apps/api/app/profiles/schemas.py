import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

Source = Literal["parsed", "interview", "user"]
Strength = Literal["weak", "ok", "strong"]


def _dates_ok(start: date | None, end: date | None) -> None:
    if start and end and end < start:
        raise ValueError("end date is before start date")


class Flags(BaseModel):
    do_not_use: bool = False
    confidential: bool = False
    sort_order: int = Field(default=0, ge=0, le=10_000)
    source: Source = "user"


class FlagsRead(Flags):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    profile_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ---- profile ---------------------------------------------------------------------------------


class Minimization(BaseModel):
    photo: bool = False
    dob: bool = False
    full_address: bool = False


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    headline: str | None = Field(default=None, max_length=300)
    summary: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)
    timezone: str | None = Field(default=None, max_length=64)
    language: str = Field(default="en", max_length=16)
    links: list[dict[str, str]] = Field(default_factory=list, max_length=30)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    headline: str | None = Field(default=None, max_length=300)
    summary: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)
    timezone: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=16)
    links: list[dict[str, str]] | None = Field(default=None, max_length=30)
    work_authorization: dict[str, Any] | None = None
    salary_prefs: dict[str, Any] | None = None
    minimization: Minimization | None = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    display_name: str
    headline: str | None
    summary: str | None
    location: str | None
    timezone: str | None
    language: str
    work_authorization: dict[str, Any]
    salary_prefs: dict[str, Any]
    links: list[dict[str, str]]
    minimization: Minimization
    is_default: bool
    created_at: datetime
    updated_at: datetime


# ---- sections --------------------------------------------------------------------------------


class ExperienceIn(Flags):
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    employment_type: str | None = Field(default=None, max_length=24)
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def _check(self):
        _dates_ok(self.start_date, self.end_date)
        if self.is_current and self.end_date:
            raise ValueError("a current role has no end date")
        return self


class ProjectIn(Flags):
    name: str = Field(min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def _check(self):
        _dates_ok(self.start_date, self.end_date)
        return self


class BulletIn(Flags):
    experience_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    text: str = Field(min_length=1, max_length=2000)
    metrics: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def _one_parent(self):
        if (self.experience_id is None) == (self.project_id is None):
            raise ValueError("a bullet belongs to exactly one experience or project")
        return self


class EducationIn(Flags):
    institution: str = Field(min_length=1, max_length=200)
    degree: str | None = Field(default=None, max_length=200)
    field: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check(self):
        _dates_ok(self.start_date, self.end_date)
        return self


class CertificationIn(Flags):
    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    kind: Literal["certification", "license"] = "certification"
    issued_on: date | None = None
    expires_on: date | None = None
    jurisdiction: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _check(self):
        _dates_ok(self.issued_on, self.expires_on)
        return self


class LanguageIn(Flags):
    name: str = Field(min_length=1, max_length=80)
    proficiency: str | None = Field(default=None, max_length=16)


class SkillIn(Flags):
    name: str = Field(min_length=1, max_length=120)
    level: str | None = Field(default=None, max_length=16)
    years: Decimal | None = Field(default=None, ge=0, le=80)
    last_used: int | None = Field(default=None, ge=1950, le=2100)
    evidence_refs: list[uuid.UUID] = Field(default_factory=list, max_length=50)


def _read(name: str, base: type[BaseModel], **extra: Any) -> type[BaseModel]:
    return create_model(  # type: ignore[call-overload]
        name,
        __base__=(FlagsRead, base),
        __config__=ConfigDict(from_attributes=True),
        **extra,
    )


def _patch(name: str, base: type[BaseModel]) -> type[BaseModel]:
    """All-optional twin of a create schema. It carries types only: the service re-validates the
    merged row against the create schema, which enforces every length and cross-field rule."""
    fields = {
        k: (f.annotation | None, None)  # pyright: ignore[reportOperatorIssue]
        for k, f in base.model_fields.items()
    }
    return create_model(name, **fields)  # type: ignore[call-overload]


ExperienceRead = _read("ExperienceRead", ExperienceIn)
ProjectRead = _read("ProjectRead", ProjectIn)
BulletRead = _read("BulletRead", BulletIn, evidence_strength=(Strength, "weak"))
EducationRead = _read("EducationRead", EducationIn)
CertificationRead = _read("CertificationRead", CertificationIn)
LanguageRead = _read("LanguageRead", LanguageIn)
SkillRead = _read("SkillRead", SkillIn)

ExperiencePatch = _patch("ExperiencePatch", ExperienceIn)
ProjectPatch = _patch("ProjectPatch", ProjectIn)
BulletPatch = _patch("BulletPatch", BulletIn)
EducationPatch = _patch("EducationPatch", EducationIn)
CertificationPatch = _patch("CertificationPatch", CertificationIn)
LanguagePatch = _patch("LanguagePatch", LanguageIn)
SkillPatch = _patch("SkillPatch", SkillIn)


class ProfileFull(ProfileRead):
    experiences: list[ExperienceRead]  # type: ignore[valid-type]
    projects: list[ProjectRead]  # type: ignore[valid-type]
    bullets: list[BulletRead]  # type: ignore[valid-type]
    education: list[EducationRead]  # type: ignore[valid-type]
    certifications: list[CertificationRead]  # type: ignore[valid-type]
    languages: list[LanguageRead]  # type: ignore[valid-type]
    skills: list[SkillRead]  # type: ignore[valid-type]


class OkRead(BaseModel):
    ok: bool = True


# ---- documents -------------------------------------------------------------------------------

DocumentKind = Literal["resume_upload", "portfolio", "generated", "paste"]
DocumentStatus = Literal["pending", "ready", "failed"]


class DocumentWarning(BaseModel):
    code: str
    message: str


class DocumentPresign(BaseModel):
    filename: str = Field(min_length=1, max_length=260)
    content_type: str | None = Field(default=None, max_length=120)
    size_bytes: int = Field(gt=0, le=10 * 1024 * 1024)
    kind: DocumentKind = "resume_upload"


class DocumentPresignRead(BaseModel):
    document_id: uuid.UUID
    upload_url: str
    r2_key: str
    expires_in: int


class DocumentDownloadRead(BaseModel):
    download_url: str
    expires_in: int


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    profile_id: uuid.UUID
    kind: DocumentKind
    filename: str
    mime: str
    size_bytes: int
    status: DocumentStatus
    ocr_used: bool
    warnings: list[DocumentWarning]
    created_at: datetime
    updated_at: datetime


class DocumentRead(DocumentListItem):
    """Includes cleaned extracted text for the review UI. Never logged."""

    extracted_text: str | None = None
    parsed: dict[str, Any] | None = None
    parse_quality: dict[str, Any] | None = None


class DocumentConfirm(BaseModel):
    """Apply a parse draft to the profile. Optional `draft` is the user-edited review payload."""

    draft: dict[str, Any] | None = None
    apply_header: bool = True


class DocumentConfirmRead(BaseModel):
    document_id: uuid.UUID
    profile_id: uuid.UUID
    header_fields: list[str]
    created: dict[str, int]


# ---- merge -----------------------------------------------------------------------------------

MergeAction = Literal["keep_existing", "take_incoming", "merge"]
AddAction = Literal["add", "skip"]
HeaderAction = Literal["keep_existing", "take_incoming"]


class MergeConflictResolution(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    action: MergeAction
    # When action=merge, choose per differing field. Omitted fields keep the existing value.
    field_actions: dict[str, HeaderAction] = Field(default_factory=dict)


class MergeAdditionAction(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    action: AddAction = "add"


class MergeHeaderAction(BaseModel):
    field: str = Field(min_length=1, max_length=64)
    action: HeaderAction


class MergeBulletAction(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    action: AddAction = "add"


class MergeResolve(BaseModel):
    """Apply merge choices for a parsed document against the current profile."""

    draft: dict[str, Any] | None = None
    resolutions: list[MergeConflictResolution] = Field(default_factory=list, max_length=200)
    additions: list[MergeAdditionAction] = Field(default_factory=list, max_length=200)
    header: list[MergeHeaderAction] = Field(default_factory=list, max_length=20)
    bullet_actions: list[MergeBulletAction] = Field(default_factory=list, max_length=400)


class MergeResolveRead(BaseModel):
    document_id: uuid.UUID
    profile_id: uuid.UUID
    stats: dict[str, Any]


# ---- answer bank -----------------------------------------------------------------------------

AnswerScope = Literal["global", "track"]
AnswerGroup = Literal["eligibility", "preferences", "eeo", "sourcing", "custom"]


class CanonicalKeyRead(BaseModel):
    key: str
    label: str
    group: AnswerGroup
    country_scoped: bool
    default_variants: list[str]
    default_answer: str
    json_hint: str | None = None


class AnswerCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9_]{1,78}$")
    country: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    question_variants: list[str] = Field(default_factory=list, max_length=40)
    answer: str = Field(default="", max_length=4000)
    answer_json: dict[str, Any] | None = None
    scope: AnswerScope = "global"
    track_id: uuid.UUID | None = None
    approved: bool = False
    sort_order: int = Field(default=0, ge=0, le=10_000)

    @model_validator(mode="after")
    def _scope_track(self):
        if self.scope == "global" and self.track_id is not None:
            raise ValueError("global answers cannot set track_id")
        if self.scope == "track" and self.track_id is None:
            raise ValueError("track-scoped answers need track_id")
        cleaned = [v.strip() for v in self.question_variants if v and v.strip()]
        if len(cleaned) > 40:
            raise ValueError("too many question variants")
        for v in cleaned:
            if len(v) > 500:
                raise ValueError("question variant is too long")
        object.__setattr__(self, "question_variants", cleaned)
        return self


class AnswerUpdate(BaseModel):
    country: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    question_variants: list[str] | None = Field(default=None, max_length=40)
    answer: str | None = Field(default=None, max_length=4000)
    answer_json: dict[str, Any] | None = None
    scope: AnswerScope | None = None
    track_id: uuid.UUID | None = None
    approved: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10_000)

    @model_validator(mode="after")
    def _variants(self):
        if self.question_variants is not None:
            cleaned = [v.strip() for v in self.question_variants if v and v.strip()]
            for v in cleaned:
                if len(v) > 500:
                    raise ValueError("question variant is too long")
            object.__setattr__(self, "question_variants", cleaned)
        return self


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    profile_id: uuid.UUID
    key: str
    country: str | None
    question_variants: list[str]
    answer: str
    answer_json: dict[str, Any] | None
    scope: AnswerScope
    track_id: uuid.UUID | None
    approved: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class AnswerSetup(BaseModel):
    """Seed missing canonical rows. Does not overwrite existing answers."""

    countries: list[str] = Field(default_factory=list, max_length=30)
    include_links: bool = True

    @model_validator(mode="after")
    def _countries(self):
        out: list[str] = []
        for c in self.countries:
            code = c.strip().upper()
            if len(code) != 2 or not code.isalpha():
                raise ValueError(f"invalid country code: {c}")
            if code not in out:
                out.append(code)
        object.__setattr__(self, "countries", out)
        return self


class AnswerSetupRead(BaseModel):
    created: int
    skipped: int
    answer_ids: list[uuid.UUID]


# ---- voice profile ---------------------------------------------------------------------------


class VoiceSampleIn(BaseModel):
    text: str = Field(min_length=20, max_length=8000)
    label: str | None = Field(default=None, max_length=80)


class VoiceSampleRead(BaseModel):
    id: uuid.UUID
    text: str
    label: str | None = None
    created_at: datetime


class VoiceStyle(BaseModel):
    summary: str = ""
    avg_sentence_length: float = 0.0
    formality: float = Field(default=0.5, ge=0, le=1)
    contraction_rate: float = Field(default=0.0, ge=0, le=1)
    vocabulary_level: Literal["plain", "mixed", "elevated"] = "mixed"
    openers: list[str] = Field(default_factory=list)
    closers: list[str] = Field(default_factory=list)
    sample_count: int = 0
    word_count: int = 0


class VoiceSamplesPut(BaseModel):
    """Replace all samples (2-5 typical). Triggers re-analysis unless analyze=false."""

    samples: list[VoiceSampleIn] = Field(min_length=1, max_length=8)
    analyze: bool = True


class VoiceUpdate(BaseModel):
    banned_phrases: list[str] | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _phrases(self):
        if self.banned_phrases is not None:
            cleaned: list[str] = []
            for p in self.banned_phrases:
                t = p.strip()
                if not t or len(t) > 80:
                    continue
                if t.lower() not in {c.lower() for c in cleaned}:
                    cleaned.append(t)
            object.__setattr__(self, "banned_phrases", cleaned[:200])
        return self


class VoiceRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    samples: list[VoiceSampleRead]
    style: VoiceStyle
    banned_phrases: list[str]
    ai_use_stance: str = ""
    analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ---- interview -------------------------------------------------------------------------------

InterviewKind = Literal["bullet_metric", "bullet_text", "skill_years", "gap_note"]
InterviewTarget = Literal["bullet", "skill", "experience"]
ProposalStatus = Literal["pending", "accepted", "rejected"]


class InterviewGapRead(BaseModel):
    id: str
    kind: InterviewKind
    target_type: InterviewTarget
    target_id: uuid.UUID
    question: str
    context: dict[str, Any] = Field(default_factory=dict)


class InterviewTurn(BaseModel):
    gap_id: str = Field(min_length=3, max_length=200)
    answer: str = Field(min_length=2, max_length=4000)


class ProposalRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    kind: InterviewKind
    target_type: InterviewTarget
    target_id: uuid.UUID
    question: str
    payload: dict[str, Any]
    status: ProposalStatus
    created_at: datetime
    updated_at: datetime


class InterviewTurnRead(BaseModel):
    proposal: ProposalRead
    next_gap: InterviewGapRead | None = None
