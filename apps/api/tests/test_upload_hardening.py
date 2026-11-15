"""Upload hardening: PDF page cap, DOCX decompressed-size cap, clear failure codes."""

from __future__ import annotations

import io
import zipfile

import pytest

from app.core.errors import AppError
from app.profiles.extract import MAX_PDF_PAGES, extract_text


def _pdf(pages: int) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    for n in range(pages):
        pdf.drawString(72, 720, f"Resume page {n + 1}")
        pdf.showPage()
    pdf.save()
    return buf.getvalue()


def test_pdf_page_cap_is_enforced():
    with pytest.raises(AppError) as exc:
        extract_text(_pdf(MAX_PDF_PAGES + 1), "application/pdf")
    assert exc.value.code == "too_many_pages"
    assert exc.value.status_code == 422


def test_pdf_at_the_cap_is_read():
    result = extract_text(_pdf(MAX_PDF_PAGES), "application/pdf")
    assert "Resume page 1" in result.text
    assert result.ocr_needed is False


def test_docx_zip_bomb_is_rejected_before_expansion():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"<doc>" + b"0" * (26 * 1024 * 1024) + b"</doc>")
    with pytest.raises(AppError) as exc:
        extract_text(
            buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    assert exc.value.code == "file_too_large"


def test_a_damaged_docx_fails_clearly():
    with pytest.raises(AppError) as exc:
        extract_text(
            b"not a zip file",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    assert exc.value.code == "invalid_docx"
