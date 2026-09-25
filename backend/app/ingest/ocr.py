"""OCR the pages that need it. Engine from settings:
- textract  : production (S3 + Textract, ap-south-1)
- tesseract : local development without AWS (needs the `tesseract` binary)
"""
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pypdfium2 as pdfium

from app.config import Settings
from app.ingest.read_pages import needs_ocr
from app.schemas.records import Page

RENDER_DPI = 200


def ocr_pages(pdf_path: Path, pages: list[Page], settings: Settings, key: str) -> list[Page]:
    todo = [p.pdf_page_no for p in pages if needs_ocr(p, settings) and p.ocr_text is None]
    if not todo:
        return pages
    if settings.ocr_engine == "textract":
        from app.aws.textract import textract_pages
        found, engine = textract_pages(pdf_path, todo, settings, key), "TEXTRACT"
    else:
        found, engine = tesseract_pages(pdf_path, todo), "TESSERACT"
    for page in pages:
        if page.pdf_page_no in found:
            page.ocr_text, page.ocr_confidence = found[page.pdf_page_no]
            page.extraction = engine
    return pages


def tesseract_pages(pdf_path: Path, page_nos: list[int]) -> dict[int, tuple[str, float | None]]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        texts = pool.map(lambda n: _tesseract_one(pdf_path, n), page_nos)
        return {n: (text, None) for n, text in zip(page_nos, texts)}


def _tesseract_one(pdf_path: Path, page_no: int) -> str:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        image = pdf[page_no - 1].render(scale=RENDER_DPI / 72).to_pil()
    finally:
        pdf.close()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "page.png"
        image.save(png)
        done = subprocess.run(["tesseract", str(png), "-"], capture_output=True,
                              text=True, check=True)
    return done.stdout
