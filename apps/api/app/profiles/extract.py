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
IMAGE_MIME = frozenset({"image/jpeg", "image/png", "image/webp"})
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 30
MAX_DOCX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class ExtractResult:
    text: str
    ocr_needed: bool
    mime: str


def sniff_mime(filename: str, declared: str | None, *, kind: str = "resume_upload") -> str:
    name = filename.lower()
    if kind == "portfolio":
        for ext, mime in (
            (".jpg", "image/jpeg"),
            (".jpeg", "image/jpeg"),
            (".png", "image/png"),
            (".webp", "image/webp"),
        ):
            if name.endswith(ext):
                return mime
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
    accepted = ALLOWED_MIME | (IMAGE_MIME if kind == "portfolio" else frozenset())
    if declared and declared.split(";")[0].strip().lower() in accepted:
        return declared.split(";")[0].strip().lower()
    if kind == "portfolio":
        raise AppError(
            "unsupported_file_type",
            "Upload a PDF, DOCX, TXT, MD, JSON, JPG, PNG, or WebP file",
            422,
        )
    raise AppError(
        "unsupported_file_type",
        "Upload a PDF, DOCX, TXT, MD, or JSON file",
        422,
    )


def validate_upload(
    filename: str, size: int, declared_mime: str | None, *, kind: str = "resume_upload"
) -> str:
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
    allowed = ALLOWED_EXTENSIONS | (IMAGE_EXTENSIONS if kind == "portfolio" else frozenset())
    if not any(lower.endswith(ext) for ext in allowed):
        if kind == "portfolio":
            raise AppError(
                "unsupported_file_type",
                "Upload a PDF, DOCX, TXT, MD, JSON, JPG, PNG, or WebP file",
                422,
            )
        raise AppError(
            "unsupported_file_type",
            "Upload a PDF, DOCX, TXT, MD, or JSON file",
            422,
        )
    return sniff_mime(filename, declared_mime, kind=kind)


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
        if len(pdf.pages) > MAX_PDF_PAGES:
            raise AppError(
                "too_many_pages",
                f"PDF has more than {MAX_PDF_PAGES} pages. Upload a shorter resume.",
                422,
                {"max_pages": MAX_PDF_PAGES},
            )
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    text = "\n\n".join(pages).strip()
    ocr_needed = len(text) < 40
    return ExtractResult(text=text, ocr_needed=ocr_needed, mime="application/pdf")


def _docx(data: bytes) -> ExtractResult:
    from docx import Document

    _check_zip_bomb(data)
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


def _check_zip_bomb(data: bytes) -> None:
    """Reject a DOCX whose declared uncompressed size is unreasonable before python-docx expands it."""
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            total = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile as exc:
        raise AppError("invalid_docx", "This Word file is damaged", 422) from exc
    if total > MAX_DOCX_UNCOMPRESSED_BYTES:
        raise AppError(
            "file_too_large",
            "This Word file expands to more than 25 MB",
            422,
            {"max_uncompressed_bytes": MAX_DOCX_UNCOMPRESSED_BYTES},
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
