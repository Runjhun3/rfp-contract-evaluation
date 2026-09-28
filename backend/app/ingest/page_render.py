"""Render bid pages as PNG: for the evidence viewer and for the LLM to read tables
whose text layer is out of reading order (CVs)."""
import io
from pathlib import Path

import pypdfium2 as pdfium

SCALE = 1.4   # ~100 dpi: readable stamps and table text, small files


def render_pngs(pdf_path: Path, page_nos: list[int]) -> dict[int, bytes]:
    """PNG bytes per 1-based page number; numbers outside the PDF are skipped."""
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        return {n: _png(pdf[n - 1]) for n in page_nos if 1 <= n <= len(pdf)}
    finally:
        pdf.close()


def _png(page: pdfium.PdfPage) -> bytes:
    buffer = io.BytesIO()
    page.render(scale=SCALE).to_pil().save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
