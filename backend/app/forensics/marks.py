"""Stamps and signatures on a scanned page: coloured ink (blue, violet or red) grouped
into marks, and on greyscale scans round seals found as circles. A stamp is round (its
box's corners nearly empty) and partly inked; a signature is long and sparse. Left out:
the letterhead band (printed logos), hollow frames (highlight boxes drawn around text),
a page with more than MAX_PER_PAGE of a kind (coloured print, not ink), and a mark that
lines of text run through (a paragraph, not a stamp: a stamp's words sit inside it).
Signatures on greyscale scans, and rectangular stamps, cannot be told from print.
"""
import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict

from app.forensics.images import Scan, to_page
from app.schemas.records import Word

HEAD = 0.15               # the top of a scan: letterheads and printed logos
SIZE = (0.06, 0.4)        # a mark's width as a share of the scan's width
MAX_PER_PAGE = 4
THROUGH = 0.3             # share of the words touching a mark that run past its edge


class Mark(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    kind: str             # STAMP or SIGNATURE
    box: tuple[int, int, int, int]   # x, y, w, h in the scan's pixels
    crop: np.ndarray      # greyscale, for comparing


def find_marks(scan: Scan, words: list[Word]) -> list[Mark]:
    """words: the OCR words inside the scan (images.inside)."""
    grey = cv2.cvtColor(scan.pixels, cv2.COLOR_BGR2GRAY)
    marks = [m for m in _inked(scan, grey) if m] or _seals(grey)
    marks = [m for m in marks if not _text_through(to_page(scan, *m.box), words)]
    kinds = {k for k in ("STAMP", "SIGNATURE")
             if sum(m.kind == k for m in marks) <= MAX_PER_PAGE}
    return [m for m in marks if m.kind in kinds]


def _inked(scan: Scan, grey: np.ndarray) -> list[Mark | None]:
    hsv = cv2.cvtColor(scan.pixels, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    ink = (sat > 35) & (val > 40) & (val < 245) & (((hue >= 95) & (hue <= 160)) |
                                                    (hue <= 10) | (hue >= 165))
    rows, cols = grey.shape
    k = max(3, cols // 40)
    closed = cv2.morphologyEx(ink.astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((k, k)))
    count, _, stats, _ = cv2.connectedComponentsWithStats(closed)
    return [_classify(grey, ink, *stats[i][:4], stats[i][4]) for i in range(1, count)]


def _classify(grey: np.ndarray, ink: np.ndarray, x: int, y: int, w: int, h: int,
              area: int) -> Mark | None:
    rows, cols = grey.shape
    if y < HEAD * rows or not SIZE[0] * cols <= w <= SIZE[1] * cols or h < 0.02 * rows:
        return None
    box = ink[y:y + h, x:x + w]
    if _hollow(box):
        return None
    fill, aspect = area / (w * h), w / h
    crop = grey[y:y + h, x:x + w]
    if 0.75 <= aspect <= 1.33 and 0.2 <= fill <= 0.8 and _round(box):
        return Mark(kind="STAMP", box=(x, y, w, h), crop=crop)
    if aspect >= 1.6 and fill <= 0.45:
        return Mark(kind="SIGNATURE", box=(x, y, w, h), crop=crop)
    return None


def _text_through(region: dict[str, float], words: list[Word]) -> bool:
    """Lines of text running through the mark's box: a paragraph, not a stamp."""
    right, bottom = region["x"] + region["w"], region["y"] + region["h"]
    touching = [w for w in words if w.x < right and w.x + w.w > region["x"]
                and w.y < bottom and w.y + w.h > region["y"]]
    past = [w for w in touching if w.x < region["x"] or w.x + w.w > right]
    return len(touching) >= 3 and len(past) > THROUGH * len(touching)


def _hollow(box: np.ndarray) -> bool:
    """Ink only along the edges of its box: a frame drawn around text, not a mark."""
    h, w = box.shape
    inner = box[h // 5:h - h // 5, w // 5:w - w // 5]
    return inner.size > 0 and inner.mean() < 0.03 and box.mean() > 0.05


def _round(box: np.ndarray) -> bool:
    """A circle leaves its box's corners nearly empty."""
    h, w = box.shape
    ch, cw = max(1, h // 6), max(1, w // 6)
    corners = [box[:ch, :cw], box[:ch, -cw:], box[-ch:, :cw], box[-ch:, -cw:]]
    return sum(c.mean() for c in corners) / 4 < 0.5 * box.mean()


def _seals(grey: np.ndarray) -> list[Mark]:
    """Round seals on a greyscale scan: circles of a seal's size below the letterhead."""
    rows, cols = grey.shape
    circles = cv2.HoughCircles(cv2.medianBlur(grey, 5), cv2.HOUGH_GRADIENT, dp=1.5,
                               minDist=cols // 6, param1=120, param2=100,
                               minRadius=int(SIZE[0] * cols / 2),
                               maxRadius=int(0.15 * cols))
    marks = []
    for cx, cy, r in (np.round(circles[0]).astype(int) if circles is not None else []):
        x, y = max(0, cx - r), max(0, cy - r)
        if y >= HEAD * rows:
            marks.append(Mark(kind="STAMP", box=(x, y, 2 * r, 2 * r),
                              crop=grey[y:y + 2 * r, x:x + 2 * r]))
    return marks
