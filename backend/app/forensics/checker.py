"""The document checks of one bid file, asked by each criterion check about its own
evidence pages (D-059, D-062), so a check's verdict includes them from the start and
they are shown with it. Opened by the eligibility job and by an evaluation on the pages
they already read and OCR'd, once their AI answers have named the evidence pages: only
those pages are analysed (D-065). It never OCRs and never asks the AI. A page's results
are worked out once and reused by every criterion that cites it.
"""
from pathlib import Path

import cv2
import pypdfium2 as pdfium

from app.config import Settings
from app.evaluate.identifiers import Found, find_identifiers
from app.forensics.coverage import MIN_TEXT, coverage
from app.forensics.finding import Finding
from app.forensics.geometry import check_words
from app.forensics.images import inside, page_scan
from app.forensics.index import bid_index
from app.forensics.layout import missing_pages, near_copy, odd_pages
from app.forensics.pixels import pixel_findings
from app.forensics.stamps import SAME_PAGE, reused
from app.forensics.words import text_layer_words
from app.schemas.records import Page


class DocumentChecker:
    def __init__(self, pdf_path: Path, pages: dict[int, Page], settings: Settings,
                 folder: Path, evidence: list[int]):
        """folder: the file's shared folder, where the index is kept; evidence: every
        page the job's checks cite, the only pages analysed and compared."""
        self.pdf = pdfium.PdfDocument(str(pdf_path))
        self.pages, self.settings = pages, settings
        self.index = bid_index(self.pdf, pages, folder, evidence)
        self.texts = {n: p.full_text() for n, p in pages.items()}
        self.done: dict[int, list[Finding]] = {}

    def close(self) -> None:
        self.pdf.close()

    def forensic(self, page_nos: list[int]) -> list[Finding]:
        """The forensic findings on these evidence pages."""
        pages = [n for n in sorted(set(page_nos)) if n in self.pages]
        return [f for n in pages for f in self._page(n)] + odd_pages(pages, self.index.scanned)

    def identifiers(self, page_nos: list[int]) -> list[Found]:
        """The identifiers on these evidence pages, with the checks needing no issuer."""
        return find_identifiers([self.pages[n] for n in sorted(set(page_nos))
                                 if n in self.pages])

    def coverage(self, page_nos: list[int]) -> str:
        """What the checks of these pages could and could not look at."""
        return coverage(page_nos, self.pages, set(self.index.boxes), self.settings)

    def _page(self, n: int) -> list[Finding]:
        if n not in self.done:
            self.done[n] = self._scan(n) if n in self.index.boxes else self._digital(n)
            if (gone := missing_pages(n, self.texts)):
                self.done[n].append(gone)
        return self.done[n]

    def _digital(self, n: int) -> list[Finding]:
        """A born-digital page: its text layer's figures."""
        if len(self.pages[n].text.strip()) < MIN_TEXT:
            return []
        return check_words(text_layer_words(self.pdf, n), n, True)

    def _scan(self, n: int) -> list[Finding]:
        """A scanned page: only the words inside the scan, never the captions round it."""
        index, words = self.index, inside(self.index.boxes[n], self.pages[n].ocr_words)
        found = reused(n, index.marks, index.thumbs, index.own)
        if (copy := near_copy(n, index.scanned, self._same_scan)):
            found.append(copy)
        dpi = self.pages[n].image_dpi or 0      # positions hold at less detail than pixels
        if dpi >= self.settings.min_position_dpi:
            found += check_words(words, n, False)
        if dpi >= self.settings.min_evidence_dpi:
            found += pixel_findings(page_scan(self.pdf, n), words, n)
        return found

    def _same_scan(self, a: int, b: int) -> bool:
        thumbs = self.index.thumbs
        return float(cv2.matchTemplate(thumbs[a], thumbs[b], cv2.TM_CCOEFF_NORMED)[0][0]) \
            >= SAME_PAGE
