"""Read every page's text layer and how much of it is covered by images.

A page needs OCR when it has almost no text OR a large image: bidders put a typed
caption ("Documentary Evidence 5: Letter of Completion") above a scanned
certificate, so a text-length rule alone misses the evidence (Deloitte: 181 pages
need OCR, only 54 have < 50 chars).
"""
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from app.config import Settings
from app.schemas.records import Page


def read_pages(pdf_path: Path) -> list[Page]:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        return [_read_page(pdf[i], i + 1) for i in range(len(pdf))]
    finally:
        pdf.close()


def needs_ocr(page: Page, settings: Settings) -> bool:
    return (len(page.text.strip()) < settings.ocr_min_chars
            or page.image_ratio >= settings.ocr_min_image_ratio)


def _read_page(page: pdfium.PdfPage, number: int) -> Page:
    text = page.get_textpage().get_text_bounded().replace("\r\n", "\n")
    return Page(pdf_page_no=number, text=text, image_ratio=_image_ratio(page))


def _image_ratio(page: pdfium.PdfPage) -> float:
    width, height = page.get_size()
    covered = 0.0
    for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=5):
        left, bottom, right, top = obj.get_bounds()
        covered += max(0.0, right - left) * max(0.0, top - bottom)
    return round(min(1.0, covered / (width * height)), 3) if width and height else 0.0
