"""Parse round-trip gate: extract rendered bytes and compare to source facts."""

from __future__ import annotations

import io
import re
from typing import Any

from app.resumes.content import ResumeContent
from app.resumes.render import parse_view


def run_parse_gate(
    content: ResumeContent,
    *,
    pdf: bytes | None,
    docx: bytes | None,
    text: str,
) -> dict[str, Any]:
    expected = parse_view(content)
    extracted_text = text or ""
    if pdf:
        extracted_text = _extract_pdf(pdf) or extracted_text
    elif docx:
        extracted_text = _extract_docx(docx) or extracted_text

    rule = _rule_parse(extracted_text)
    diagnostics: list[str] = []
    ok = True

    def _need(label: str, value: str | None) -> None:
        nonlocal ok
        if not value:
            return
        if value.lower() not in extracted_text.lower():
            ok = False
            diagnostics.append(f"missing_{label}:{value}")

    _need("name", expected.get("name"))
    _need("email", expected.get("email"))
    for emp in expected.get("employers") or []:
        _need("title", emp.get("title"))
        _need("company", emp.get("company"))

    # Section order
    exp_headings = expected.get("sections") or []
    positions = []
    low = extracted_text.lower()
    for h in exp_headings:
        idx = low.find(h.lower())
        positions.append(idx)
        if idx < 0:
            ok = False
            diagnostics.append(f"missing_section:{h}")
    present = [p for p in positions if p >= 0]
    if present != sorted(present):
        ok = False
        diagnostics.append("section_order_mismatch")

    return {
        "ok": ok,
        "diagnostics": diagnostics,
        "extracted": {
            "chars": len(extracted_text),
            "rule": rule,
            "expected": expected,
        },
    }


def _extract_pdf(data: bytes) -> str:
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            return ""


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document

        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""


def _rule_parse(text: str) -> dict[str, Any]:
    email = None
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if m:
        email = m.group(0)
    return {"email": email, "lines": len(text.splitlines())}
