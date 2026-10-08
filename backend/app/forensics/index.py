"""What the forensic checks compare a criterion's evidence pages against, from pages
already read and OCR'd (no OCR, no AI): each scan's stamps and signatures, a small copy
of it, its words placed within it, and the bidder's own repeated images.

Only the evidence pages a job's checks cite are analysed (D-065), never the whole bid:
each page once per bid file, kept next to the file's pages (index-v2.pkl) and reused by
every later job. A job sees only its own evidence pages, so what it finds does not
depend on what other jobs analysed before. The bidder's own images are found from the
whole file, which reads only small images and is quick.
"""
import pickle
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
from pydantic import BaseModel, ConfigDict, Field

from app.forensics.images import in_scan, inside, own_images, page_scan, to_page
from app.forensics.marks import find_marks
from app.forensics.stamps import Placed, norm, thumb
from app.schemas.records import Page, Word

NAME = "index-v2.pkl"     # a new version when what is kept changes


class BidIndex(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    own: list[np.ndarray]              # the bidder's repeated images, normalised
    seen: set[int] = Field(default_factory=set)       # pages analysed (scanned or not)
    boxes: dict[int, dict] = Field(default_factory=dict)   # each scan's place on its page
    marks: dict[int, list[Placed]] = Field(default_factory=dict)   # its stamps, signatures
    thumbs: dict[int, np.ndarray] = Field(default_factory=dict)    # each scan, small
    scanned: dict[int, list[Word]] = Field(default_factory=dict)   # words within each scan


def bid_index(pdf: pdfium.PdfDocument, pages: dict[int, Page], folder: Path,
              page_nos: list[int]) -> BidIndex:
    """The index of these pages only; pages not analysed before are analysed and kept."""
    path = folder / NAME
    index = pickle.loads(path.read_bytes()) if path.exists() else \
        BidIndex(own=[norm(o) for o in own_images(pdf)])     # written by this function only
    wanted = {n for n in page_nos if n in pages}
    if wanted - index.seen:
        _add(index, pdf, pages, wanted - index.seen)
        folder.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".part")                     # never a half-written index
        part.write_bytes(pickle.dumps(index))
        part.replace(path)
    return BidIndex(own=index.own, seen=wanted,
                    **{name: {n: v for n, v in getattr(index, name).items() if n in wanted}
                       for name in ("boxes", "marks", "thumbs", "scanned")})


def _add(index: BidIndex, pdf: pdfium.PdfDocument, pages: dict[int, Page],
         page_nos: set[int]) -> None:
    for n in sorted(page_nos):
        index.seen.add(n)
        scan = page_scan(pdf, n) if pages[n].image_dpi else None
        if scan is None:
            continue
        words = inside(scan.box, pages[n].ocr_words)
        index.boxes[n] = scan.box
        index.marks[n] = [(m, to_page(scan, *m.box)) for m in find_marks(scan, words)]
        index.thumbs[n] = thumb(cv2.cvtColor(scan.pixels, cv2.COLOR_BGR2GRAY))
        index.scanned[n] = in_scan(scan.box, pages[n].ocr_words)
