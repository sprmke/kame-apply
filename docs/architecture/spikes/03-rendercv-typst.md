# Spike 3: RenderCV / Typst

**Date:** 2026-10-28 · **Decision: KEEP** · Tested: RenderCV 2.8 (`rendercv[full]`), macOS arm64.

| Check | Result |
| --- | --- |
| Render sample CV YAML → PDF | 0.62-0.66 s per render (3 runs), well under the 2 s budget. |
| Real text layer | `pdfplumber` extracts text; no image-only content. |
| Reading order | Headings extracted in document order (Education → Experience); header contact line first. |
| Other outputs | The same run also emits `.typ`, `.md`, `.html`, PNG pages, which helps the parse round-trip gate and the preview. |
| Linux arm64 | `typst` 0.15.0 manylinux aarch64 wheel exists; to re-time on the Oracle VM (spike 2). |

Notes: RenderCV adds a "Last updated" line and a default two-page sample; the Phase 8 renderer must control the template and page budget, and run the parse round-trip against the *source facts*, not just plain extraction. Use `pdfplumber` (MIT), not PyMuPDF (AGPL).
