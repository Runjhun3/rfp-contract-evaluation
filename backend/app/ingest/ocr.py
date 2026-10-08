"""OCR the pages that need it. Engine from settings:
- textract  : production (S3 + Textract, ap-south-1)
- tesseract : local development without AWS (needs the `tesseract` binary)
Each OCR'd page keeps its text, its average confidence and its words with their boxes.
"""
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pypdfium2 as pdfium

from app.config import Settings
from app.ingest.read_pages import needs_ocr
from app.schemas.records import Page, Word

RENDER_DPI = 200
Found = dict[int, tuple[str, float | None, list[Word]]]


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
            page.ocr_text, page.ocr_confidence, page.ocr_words = found[page.pdf_page_no]
            page.extraction = engine
    return pages


def tesseract_pages(pdf_path: Path, page_nos: list[int]) -> Found:
    """PDFium is not thread-safe: the pages are rendered one by one, then read by
    Tesseract in parallel."""
    with tempfile.TemporaryDirectory() as tmp:
        sizes = _render(pdf_path, page_nos, Path(tmp))
        with ThreadPoolExecutor(max_workers=4) as pool:
            tsvs = pool.map(lambda n: _tesseract(Path(tmp) / f"{n}.png"), page_nos)
            return {n: read_tsv(tsv, *sizes[n]) for n, tsv in zip(page_nos, tsvs)}


def _render(pdf_path: Path, page_nos: list[int], folder: Path) -> dict[int, tuple[int, int]]:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        sizes = {}
        for n in page_nos:
            image = pdf[n - 1].render(scale=RENDER_DPI / 72).to_pil()
            image.save(folder / f"{n}.png")
            sizes[n] = image.size
        return sizes
    finally:
        pdf.close()


def _tesseract(png: Path) -> str:
    return subprocess.run(["tesseract", str(png), "-", "tsv"], capture_output=True,
                          encoding="utf-8", errors="replace", check=True).stdout


def read_tsv(tsv: str, width: int, height: int) -> tuple[str, float | None, list[Word]]:
    """Tesseract's word table: the text line by line, the mean confidence, the words."""
    lines: dict[tuple, list[str]] = {}
    words = []
    for row in tsv.splitlines()[1:]:
        cells = row.split("\t")
        if len(cells) < 12 or cells[0] != "5" or not cells[11].strip():
            continue
        left, top, w, h, conf = (float(c) for c in cells[6:11])
        lines.setdefault(tuple(cells[1:5]), []).append(cells[11])
        words.append(Word(text=cells[11], x=left / width, y=top / height, w=w / width,
                          h=h / height, conf=round(max(conf, 0) / 100, 3)))
    text = "\n".join(" ".join(line) for line in lines.values())
    confidence = round(sum(w.conf for w in words) / len(words), 3) if words else None
    return text, confidence, words
