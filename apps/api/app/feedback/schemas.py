from pydantic import BaseModel, Field, field_validator


class FeedbackCreate(BaseModel):
    category: str = Field(default="general", max_length=40)
    message: str = Field(min_length=10, max_length=4000)
    page: str | None = Field(default=None, max_length=200)

    @field_validator("message")
    @classmethod
    def _no_obvious_pii(cls, v: str) -> str:
        # Soft guard: refuse emails, phones, and government-id shaped digit groups.
        import re

        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", v):
            raise ValueError("Remove email addresses from feedback")
        digits = re.sub(r"\D", "", v)
        if len(digits) >= 8:
            raise ValueError("Remove phone numbers and ID-like digit sequences from feedback")
        if re.search(r"\b\d{3}[-.\s]\d{2,3}[-.\s]\d{4}\b", v):
            raise ValueError("Remove phone numbers and ID-like digit sequences from feedback")
        return v.strip()


class FeedbackRead(BaseModel):
    ok: bool = True
    issue_url: str | None = None
