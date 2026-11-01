"""ResumeContent: structured resume with evidence refs on every line (PRD P1)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class ContactBlock(BaseModel):
    full_name: str = ""
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)


class ResumeLine(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    evidence_refs: list[str] = Field(default_factory=list)
    unverified: bool = False


class ResumeItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    subtitle: str | None = None
    location: str | None = None
    start: str | None = None
    end: str | None = None
    is_current: bool = False
    lines: list[ResumeLine] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ResumeSection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: Literal[
        "summary",
        "experience",
        "projects",
        "education",
        "skills",
        "certifications",
        "languages",
        "custom",
    ]
    heading: str
    items: list[ResumeItem] = Field(default_factory=list)
    lines: list[ResumeLine] = Field(default_factory=list)  # summary / skills blobs


class ResumeContent(BaseModel):
    schema_version: int = 1
    contact: ContactBlock = Field(default_factory=ContactBlock)
    summary: ResumeLine | None = None
    sections: list[ResumeSection] = Field(default_factory=list)
    target_role: str | None = None
    locale: str = "en"
    meta: dict[str, Any] = Field(default_factory=dict)

    def all_lines(self) -> list[ResumeLine]:
        out: list[ResumeLine] = []
        if self.summary:
            out.append(self.summary)
        for sec in self.sections:
            out.extend(sec.lines)
            for item in sec.items:
                out.extend(item.lines)
        return out

    def plain_text(self) -> str:
        parts: list[str] = []
        c = self.contact
        parts.append(c.full_name)
        contact_bits = [x for x in (c.email, c.phone, c.location, *c.links) if x]
        if contact_bits:
            parts.append(" | ".join(contact_bits))
        if self.summary and self.summary.text:
            parts.append("")
            parts.append("SUMMARY")
            parts.append(self.summary.text)
        for sec in self.sections:
            parts.append("")
            parts.append(sec.heading.upper())
            for line in sec.lines:
                parts.append(f"- {line.text}" if sec.kind == "skills" else line.text)
            for item in sec.items:
                head = f"{item.title}, {item.subtitle}" if item.subtitle else item.title
                end = item.end or ("Present" if item.is_current else None)
                dates = " - ".join(x for x in (item.start, end) if x)
                parts.append(head + (f" ({dates})" if dates else ""))
                if item.location:
                    parts.append(item.location)
                for line in item.lines:
                    parts.append(f"- {line.text}")
        return "\n".join(parts).strip() + "\n"
