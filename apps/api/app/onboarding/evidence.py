"""Evidence spans: an exact quoted line from the sanitized resume text."""

from __future__ import annotations

import uuid

from app.onboarding import schemas as s


def find_span(text: str, needle: str) -> tuple[int, int] | None:
    if not needle:
        return None
    index = text.casefold().find(needle.casefold())
    if index < 0:
        return None
    return index, index + len(needle)


def line_around(text: str, start: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    return text[line_start : line_end if line_end != -1 else len(text)].strip()


def evidence(document_id: uuid.UUID, text: str, quote: str) -> list[s.EvidenceRef]:
    """Evidence for one claimed value, or an empty list when the text does not contain it."""
    quote = (quote or "").strip()
    if not quote:
        return []
    span = find_span(text, quote)
    if span is None:
        return []
    quote_text = line_around(text, span[0])[:200] or quote[:200]
    line_start = text.rfind("\n", 0, span[0]) + 1
    return [
        s.EvidenceRef(
            document_id=document_id,
            quote=quote_text,
            start=line_start,
            end=line_start + len(quote_text),
        )
    ]
