"""Render one bid page as PNG for the evidence viewer, cached on disk."""
import io
from pathlib import Path

import pypdfium2 as pdfium

from app import files
from app.config import Settings

SCALE = 1.4   # ~100 dpi: readable stamps, small files


def page_png(settings: Settings, key: str, page_no: int) -> bytes | None:
    cache = Path(settings.runs_dir) / "_page_cache" / key.replace("/", "_") / f"{page_no}.png"
    if cache.exists():
        return cache.read_bytes()
    pdf = pdfium.PdfDocument(str(files.local_path(settings, key)))
    try:
        if not 1 <= page_no <= len(pdf):
            return None
        image = pdf[page_no - 1].render(scale=SCALE).to_pil()
    finally:
        pdf.close()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(buffer.getvalue())
    return buffer.getvalue()
