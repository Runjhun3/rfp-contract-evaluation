"""A page's scanned image as stored in the PDF (not re-rendered: rendering smooths the
traces the pixel checks look at), with where it sits on the page; and the small images
the bidder repeats across its pages (its own seal and signature on each page)."""
import hashlib

import cv2
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from pydantic import BaseModel, ConfigDict

from app.schemas.records import Word

MIN_AREA = 0.2            # an image covering this share of the page is a scan


class Scan(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pixels: np.ndarray    # BGR, as OpenCV reads it
    box: dict[str, float] # x, y, w, h on the page, fractions from the top left
    jpeg: bool            # stored as JPEG: the re-compression check applies
    dpi: int


def page_scan(pdf: pdfium.PdfDocument, page_no: int) -> Scan | None:
    """The page's largest image if it covers a fifth of the page, else None."""
    page = pdf[page_no - 1]
    width, height = page.get_size()
    best, best_area = None, MIN_AREA * width * height
    for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=5):
        left, bottom, right, top = obj.get_bounds()
        area = max(0.0, right - left) * max(0.0, top - bottom)
        if area >= best_area:
            best, best_area, bounds = obj, area, (left, bottom, right, top)
    if best is None:
        return None
    left, bottom, right, top = bounds
    pixels = np.array(best.get_bitmap(render=False).to_pil().convert("RGB"))[:, :, ::-1]
    return Scan(pixels=np.ascontiguousarray(pixels), jpeg="DCTDecode" in best.get_filters(),
                box={"x": left / width, "y": 1 - top / height, "w": (right - left) / width,
                     "h": (top - bottom) / height},
                dpi=round(pixels.shape[1] / ((right - left) / 72)))


def to_page(scan: Scan, x: int, y: int, w: int, h: int) -> dict[str, float]:
    """A pixel box of the scan as a region of the page (fractions from the top left)."""
    rows, cols = scan.pixels.shape[:2]
    b = scan.box
    return {"x": b["x"] + x / cols * b["w"], "y": b["y"] + y / rows * b["h"],
            "w": w / cols * b["w"], "h": h / rows * b["h"]}


def inside(box: dict[str, float], words: list[Word]) -> list[Word]:
    """The words whose middle lies inside the scan: a caption the bidder typed above a
    scan is not part of it."""
    return [w for w in words
            if box["x"] <= w.x + w.w / 2 <= box["x"] + box["w"]
            and box["y"] <= w.y + w.h / 2 <= box["y"] + box["h"]]


def in_scan(box: dict[str, float], words: list[Word]) -> list[Word]:
    """The words inside the scan, placed as fractions of the scan itself (so scans
    pasted at different places on their pages can be compared)."""
    return [w.model_copy(update={"x": (w.x - box["x"]) / box["w"],
                                 "y": (w.y - box["y"]) / box["h"],
                                 "w": w.w / box["w"], "h": w.h / box["h"]})
            for w in inside(box, words)]


def own_images(pdf: pdfium.PdfDocument, share: float = 0.3) -> list[np.ndarray]:
    """The small images on at least `share` of the pages (the bidder signing and sealing
    each page), greyscale: a stamp or signature like one of them is the bidder's own."""
    seen: dict[str, tuple[set[int], object]] = {}
    for n in range(len(pdf)):
        page = pdf[n]
        width, height = page.get_size()
        for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=5):
            left, bottom, right, top = obj.get_bounds()
            if (right - left) * (top - bottom) >= 0.05 * width * height:
                continue
            key = hashlib.sha1(bytes(obj.get_data(decode_simple=False))).hexdigest()
            seen.setdefault(key, (set(), obj))[0].add(n)
    common = max(3, share * len(pdf))
    return [cv2.cvtColor(np.array(obj.get_bitmap(render=False).to_pil().convert("RGB")),
                         cv2.COLOR_RGB2GRAY)
            for pages, obj in seen.values() if len(pages) >= common]
