import uuid
from datetime import datetime

from pydantic import BaseModel, Field, SecretStr


class CredentialCreate(BaseModel):
    provider: str = Field(max_length=24)
    api_key: SecretStr | None = Field(default=None, min_length=8, max_length=500)
    label: str | None = Field(default=None, max_length=80)
    base_url: str | None = Field(default=None, max_length=300)


class CredentialRead(BaseModel):
    id: uuid.UUID
    provider: str
    label: str | None
    key_hint: str | None
    base_url: str | None
    status: str
    last_tested_at: datetime | None
    created_at: datetime


class CredentialTestRead(BaseModel):
    status: str  # valid | invalid | error
    detail: str | None = None


class TierChoice(BaseModel):
    provider: str
    model: str = Field(max_length=120)


class AiSettingsRead(BaseModel):
    monthly_budget_cents: int
    tier_models: dict[str, TierChoice]
    fallback_enabled: bool


class AiSettingsUpdate(BaseModel):
    monthly_budget_cents: int | None = Field(default=None, ge=0, le=1_000_000)
    tier_models: dict[str, TierChoice] | None = None
    fallback_enabled: bool | None = None


class UsageDay(BaseModel):
    day: datetime
    cost_micros: int
    calls: int


class UsageFeature(BaseModel):
    feature: str
    cost_micros: int
    calls: int


class UsageRead(BaseModel):
    month_start: datetime
    budget_cents: int
    spent_micros: int
    by_day: list[UsageDay]
    by_feature: list[UsageFeature]


class ProviderRead(BaseModel):
    id: str
    label: str
    needs_key: bool
    tier_models: dict[str, str]


class OkRead(BaseModel):
    ok: bool = True
