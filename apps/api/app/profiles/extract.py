"""Pull plain text from resume uploads. OCR is flagged when a PDF has no text layer; Tesseract
itself is optional and not required for the happy path (research/05 §2)."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass

from app.core.errors import AppError

ALLOWED_MIME = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "application/json",
    }
)
ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx", ".txt", ".md", ".json"})
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class ExtractResult:
    text: str
    ocr_needed: bool
    mime: str


def sniff_mime(filename: str, declared: str | None) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if name.endswith(".md"):
        return "text/markdown"
    if name.endswith(".json"):
        return "application/json"
    if name.endswith(".txt"):
        return "text/plain"
    if declared and declared.split(";")[0].strip().lower() in ALLOWED_MIME:
        return declared.split(";")[0].strip().lower()
    raise AppError(
        "unsupported_file_type",
        "Upload a PDF, DOCX, TXT, MD, or JSON file",
        422,
    )


def validate_upload(filename: str, size: int, declared_mime: str | None) -> str:
    if size <= 0:
        raise AppError("empty_file", "File is empty", 422)
    if size > MAX_UPLOAD_BYTES:
        raise AppError(
            "file_too_large",
            "File must be 10 MB or smaller",
            422,
            {"max_bytes": MAX_UPLOAD_BYTES},
        )
    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise AppError(
            "unsupported_file_type",
            "Upload a PDF, DOCX, TXT, MD, or JSON file",
            422,
        )
    return sniff_mime(filename, declared_mime)


def extract_text(data: bytes, mime: str) -> ExtractResult:
    if mime == "application/pdf":
        return _pdf(data)
    if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _docx(data)
    if mime == "application/json":
        return _json(data)
    # text/plain and text/markdown
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    return ExtractResult(text=text, ocr_needed=False, mime=mime)


def _pdf(data: bytes) -> ExtractResult:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    text = "\n\n".join(pages).strip()
    ocr_needed = len(text) < 40
    return ExtractResult(text=text, ocr_needed=ocr_needed, mime="application/pdf")


def _docx(data: bytes) -> ExtractResult:
    from docx import Document

    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return ExtractResult(
        text="\n".join(parts),
        ocr_needed=False,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def _json(data: bytes) -> ExtractResult:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppError("invalid_json", "JSON resume could not be read", 422) from exc
    # Prefer a readable dump so the LLM parse step (slice 3) still has structure.
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    return ExtractResult(text=text, ocr_needed=False, mime="application/json")


def scan_bytes(_data: bytes) -> None:
    """AV placeholder. ClamAV runs in the worker later; local/test always pass."""
    return None
