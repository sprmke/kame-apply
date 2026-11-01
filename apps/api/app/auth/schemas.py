import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.passwords import MAX_LENGTH, MIN_LENGTH


def _check_password(v: str) -> str:
    if not (MIN_LENGTH <= len(v) <= MAX_LENGTH):
        raise ValueError(f"password must be {MIN_LENGTH} to {MAX_LENGTH} characters")
    return v


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str | None = Field(default=None, max_length=120)

    _pw = field_validator("password")(_check_password)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=MAX_LENGTH)


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str

    _pw = field_validator("password")(_check_password)


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    timezone: str
    locale: str
    email_verified: bool


class AuthRead(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (OAuth token type, not a secret)
    expires_in: int
    user: UserRead


class AcceptedRead(BaseModel):
    ok: bool = True


class MeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=16)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        if v is None:
            return v
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown timezone") from None
        return v


class SessionRead(BaseModel):
    id: uuid.UUID
    user_agent: str | None
    ip: str | None
    created_at: datetime
    last_used_at: datetime
    current: bool


class ProvidersRead(BaseModel):
    google: bool


class OAuthUrlRead(BaseModel):
    url: str


class MeRead(UserRead):
    has_password: bool
    providers: list[str]
