"""Stamp and signature checks on a criterion's evidence pages, within one bid (D-059):
the same stamp or signature image as on another page of the bid. A physical stamp or a
pen never leaves the same impression twice, so a near pixel-identical copy suggests it
was pasted. Left out: two pages that are the same scan shown twice (e.g. one certificate
under two criteria), and the bidder's own stamp and signature (like an image the bidder
repeats on its pages). A stamp's words are not judged (D-063): a genuine issuer's,
auditor's or notary's seal carries words found nowhere else on its page.
"""
import cv2
import numpy as np

from app.forensics.finding import Finding
from app.forensics.marks import Mark

SAME = 0.97               # correlation of two crops above which they are one image
SIDE = 96                 # crops are compared at this size
OWN_LIKE = 0.85           # correlation with one of the bidder's own images
SAME_PAGE = 0.9           # whole-page correlation of a scan shown twice

Placed = tuple[Mark, dict]   # a mark and its region on the page


def norm(crop: np.ndarray) -> np.ndarray:
    """A crop or an image at the size marks are compared at."""
    return cv2.resize(crop, (SIDE, SIDE), interpolation=cv2.INTER_AREA).astype(np.float32)


def thumb(grey: np.ndarray) -> np.ndarray:
    """A whole scan, small, to tell a page shown twice."""
    return cv2.resize(grey, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)


def is_own(mark: Mark, own: list[np.ndarray]) -> bool:
    """own: the bidder's repeated images, already norm()ed."""
    crop = norm(mark.crop)
    return any(_corr(crop, o) >= OWN_LIKE for o in own)


def reused(page: int, marks: dict[int, list[Placed]], thumbs: dict[int, np.ndarray],
           own: list[np.ndarray]) -> list[Finding]:
    """The marks on one page that are the same image as a mark on another page."""
    found = []
    for mark, region in marks.get(page, []):
        if is_own(mark, own):
            continue
        crop = norm(mark.crop)
        others = sorted(p for p, placed in marks.items()
                        if p != page and _corr(thumbs[p], thumbs[page]) < SAME_PAGE
                        and any(m.kind == mark.kind and _corr(crop, norm(m.crop)) >= SAME
                                for m, _ in placed))
        if others:
            pages = ", ".join(f"p.{p}" for p in others)
            found.append(Finding(kind=f"{mark.kind}_REUSED", page=page, region=region,
                                 score=2.0,
                                 note=f"This {mark.kind.lower()} is the same image as on "
                                      f"{pages}: a real one never prints exactly alike."))
    return found


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)[0][0])
