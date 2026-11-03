"""Render ResumeContent to PDF / DOCX / plain text. ATS-safe single column."""

from __future__ import annotations

import io
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Any

from app.resumes.content import ResumeContent

TEMPLATES = ("classic", "compact", "modern", "serif")


@dataclass
class RenderResult:
    pdf: bytes | None
    docx: bytes
    text: str
    engine: str
    filename_base: str


def _safe_name(content: ResumeContent) -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "-", content.contact.full_name or "Resume").strip("-")
    role = re.sub(r"[^A-Za-z0-9]+", "-", content.target_role or "Role").strip("-")
    return f"{name}-{role}"[:120] or "Resume"


def render_all(
    content: ResumeContent,
    *,
    template: str = "classic",
    page_size: str = "letter",
    broken: bool = False,
) -> RenderResult:
    """Render all formats. `broken=True` intentionally fails parse gate (dev test)."""
    text = content.plain_text()
    if broken:
        # Scramble reading order / hide contact for gate failure tests
        text = "HIDDEN\n" + "\n".join(reversed(text.splitlines()))
    docx = render_docx(content, plain_override=text if broken else None)
    pdf, engine = render_pdf(content, template=template, page_size=page_size, broken=broken)
    return RenderResult(
        pdf=pdf,
        docx=docx,
        text=text,
        engine=engine,
        filename_base=_safe_name(content),
    )


def render_docx(content: ResumeContent, *, plain_override: str | None = None) -> bytes:
    from docx import Document

    doc = Document()
    if plain_override:
        for line in plain_override.splitlines():
            doc.add_paragraph(line)
    else:
        c = content.contact
        doc.add_heading(c.full_name or "Candidate", level=1)
        bits = [x for x in (c.email, c.phone, c.location, *c.links) if x]
        if bits:
            doc.add_paragraph(" | ".join(bits))
        if content.summary:
            doc.add_heading("Summary", level=2)
            doc.add_paragraph(content.summary.text)
        for sec in content.sections:
            doc.add_heading(sec.heading, level=2)
            for line in sec.lines:
                doc.add_paragraph(line.text, style="List Bullet" if sec.kind == "skills" else None)
            for item in sec.items:
                head = f"{item.title}, {item.subtitle}" if item.subtitle else item.title
                end = item.end or ("Present" if item.is_current else None)
                dates = " - ".join(x for x in (item.start, end) if x)
                p = doc.add_paragraph()
                run = p.add_run(head + (f" ({dates})" if dates else ""))
                run.bold = True
                for line in item.lines:
                    doc.add_paragraph(line.text, style="List Bullet")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def render_pdf(
    content: ResumeContent,
    *,
    template: str = "classic",
    page_size: str = "letter",
    broken: bool = False,
) -> tuple[bytes | None, str]:
    """Prefer RenderCV/Typst; fall back to reportlab text PDF for CI."""
    if os.environ.get("RESUME_PDF_ENGINE", "").lower() == "none":
        return None, "none"
    if not broken:
        pdf = _rendercv_pdf(content, template=template, page_size=page_size)
        if pdf:
            return pdf, "rendercv"
    try:
        return _reportlab_pdf(content, page_size=page_size, broken=broken), "reportlab"
    except Exception:
        return None, "unavailable"


def _rendercv_pdf(content: ResumeContent, *, template: str, page_size: str) -> bytes | None:
    """Best-effort RenderCV render. Returns None if typst/rendercv unavailable."""
    import importlib
    import importlib.util
    import tempfile
    from pathlib import Path

    if importlib.util.find_spec("rendercv") is None:
        return None

    yaml_body = _to_rendercv_yaml(content, page_size=page_size)
    with tempfile.TemporaryDirectory() as td:
        yml = Path(td) / "resume.yaml"
        yml.write_text(yaml_body, encoding="utf-8")
        try:
            cli = importlib.import_module("rendercv.cli")
            cli.render_a_resume_from_a_yaml_file(str(yml))
        except Exception:
            try:
                rc = importlib.import_module("rendercv")
                data_model = rc.data.read_input_file(str(yml))
                rc.renderer.render(data_model)
            except Exception:
                return None
        pdfs = list(Path(td).rglob("*.pdf"))
        if not pdfs:
            return None
        return pdfs[0].read_bytes()


def _to_rendercv_yaml(content: ResumeContent, *, page_size: str) -> str:
    c = content.contact
    lines = [
        "cv:",
        f"  name: {c.full_name or 'Candidate'}",
    ]
    if c.email:
        lines.append(f"  email: {c.email}")
    if c.phone:
        lines.append(f"  phone: '{c.phone}'")
    if c.location:
        lines.append(f"  location: {c.location}")
    if content.summary:
        lines.append("  sections:")
        lines.append("    summary:")
        lines.append(f"      - '{content.summary.text.replace(chr(39), '')}'")
    lines.append("design:")
    lines.append("  page:")
    lines.append(f"    size: {'a4' if page_size == 'a4' else 'us-letter'}")
    return "\n".join(lines) + "\n"


def _reportlab_pdf(
    content: ResumeContent, *, page_size: str = "letter", broken: bool = False
) -> bytes:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    size = A4 if page_size == "a4" else letter
    c = canvas.Canvas(buf, pagesize=size)
    _width, height = size
    y = height - 54
    text = content.plain_text()
    if broken:
        # Omit contact and scramble so parse gate fails
        lines = [ln for ln in text.splitlines() if "@" not in ln and "Phone" not in ln]
        text = "\n".join(reversed(lines))
    for line in text.splitlines():
        # Wrap instead of truncating: a long bullet must not lose its tail in the PDF.
        chunks = textwrap.wrap(line, width=110) or [""]
        for chunk in chunks:
            if y < 54:
                c.showPage()
                y = height - 54
            c.setFont("Helvetica", 10)
            c.drawString(54, y, chunk)
            y -= 14
    c.save()
    return buf.getvalue()


def parse_view(content: ResumeContent) -> dict[str, Any]:
    """What a simple ATS-like parser extracts (rule-based)."""
    employers = []
    for sec in content.sections:
        if sec.kind != "experience":
            continue
        for it in sec.items:
            employers.append(
                {
                    "title": it.title,
                    "company": it.subtitle,
                    "start": it.start,
                    "end": it.end or ("Present" if it.is_current else None),
                }
            )
    return {
        "name": content.contact.full_name,
        "email": content.contact.email,
        "phone": content.contact.phone,
        "sections": [s.heading for s in content.sections],
        "employers": employers,
        "skills": [line.text for s in content.sections if s.kind == "skills" for line in s.lines],
    }
