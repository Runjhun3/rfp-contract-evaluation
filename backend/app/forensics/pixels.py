"""Pixel checks on a scan within one bid (D-058), each on the original stored image and
only when it is sharp enough (MIN_EVIDENCE_DPI): a scan already re-compressed or blurred
hides these traces and would only give false alarms.
  - re-compression (JPEG only): a figure that re-compresses unlike the words around it
    may have been edited after the scan was made,
  - noise: a figure much smoother or grainier than the other words on its line,
  - copied patches: one part of the page (outside its text) repeated elsewhere on it,
    as a copied stamp or signature is.
"""
from statistics import median

import cv2
import numpy as np

from app.forensics.finding import Finding, is_figure
from app.forensics.lines import group_lines
from app.forensics.images import Scan, to_page
from app.schemas.records import Word

LIMITS = {"recompress": 2.5, "noise": 3.0, "copies": 12}


def pixel_findings(scan: Scan, words: list[Word], page: int) -> list[Finding]:
    grey = cv2.cvtColor(scan.pixels, cv2.COLOR_BGR2GRAY)
    boxes = {id(w): box for w in words if (box := _px(scan, w))}
    words = [w for w in words if id(w) in boxes]
    found = _regions(grey, scan, words, boxes, page)
    if not boxes:                 # without the text's place, letters would match letters
        return found
    return found + _copies(grey, scan, list(boxes.values()), page)


def _regions(grey: np.ndarray, scan: Scan, words: list[Word], boxes: dict,
             page: int) -> list[Finding]:
    errors = _recompression(scan.pixels) if scan.jpeg else None
    level = (median(_mean(errors, b) for b in boxes.values()) if errors is not None
             and boxes else None)
    found = []
    for line in group_lines(words):
        noise = {id(w): _noise(grey, boxes[id(w)]) for w in line}
        usual = median(noise.values()) if len(line) >= 4 else None
        for w in (w for w in line if is_figure(w)):
            reasons = []
            if level and _mean(errors, boxes[id(w)]) > LIMITS["recompress"] * level:
                reasons.append("it re-compresses unlike the words around it")
            if usual and noise[id(w)] and not 1 / LIMITS["noise"] < \
                    noise[id(w)] / usual < LIMITS["noise"]:
                reasons.append("its grain differs from the rest of its line")
            if reasons:
                found.append(Finding(kind="PIXELS", page=page, score=1.5,
                                     region=to_page(scan, *boxes[id(w)]),
                                     note=f"\"{w.text}\": " + "; ".join(reasons)))
    return found


def _copies(grey: np.ndarray, scan: Scan, text: list[tuple], page: int) -> list[Finding]:
    """Matching keypoints at one common offset, outside the text, mean a copied patch."""
    mask = np.full(grey.shape, 255, np.uint8)
    for x, y, w, h in text:
        mask[y:y + h, x:x + w] = 0
    orb = cv2.ORB_create(1500)
    points, desc = orb.detectAndCompute(grey, mask)
    if desc is None or len(points) < 2 * LIMITS["copies"]:
        return []
    shifts = {}
    for pair in cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(desc, desc, k=2):
        if len(pair) < 2 or pair[1].distance > 20:
            continue
        a, b = points[pair[1].queryIdx].pt, points[pair[1].trainIdx].pt
        shift = (round((b[0] - a[0]) / 8), round((b[1] - a[1]) / 8))
        if abs(shift[0]) + abs(shift[1]) > 4:
            shifts.setdefault(shift, []).append(a)
    best = max(shifts.values(), key=len, default=[])
    if len(best) < LIMITS["copies"]:
        return []
    xs, ys = [int(p[0]) for p in best], [int(p[1]) for p in best]
    box = (min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
    return [Finding(kind="COPIED_PATCH", page=page, region=to_page(scan, *box), score=2.0,
                    note=f"A part of the page ({len(best)} matching points) appears again "
                         "elsewhere on it, as a copied stamp or signature would.")]


def _recompression(pixels: np.ndarray) -> np.ndarray:
    ok, encoded = cv2.imencode(".jpg", pixels, [cv2.IMWRITE_JPEG_QUALITY, 90])
    again = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    return cv2.cvtColor(cv2.absdiff(pixels, again), cv2.COLOR_BGR2GRAY).astype(np.float32)


def _noise(grey: np.ndarray, box: tuple) -> float:
    x, y, w, h = box
    patch = grey[y:y + h, x:x + w]
    return float(cv2.Laplacian(patch, cv2.CV_64F).var()) if patch.size >= 16 else 0.0


def _mean(values: np.ndarray, box: tuple) -> float:
    x, y, w, h = box
    patch = values[y:y + h, x:x + w]
    return float(patch.mean()) if patch.size else 0.0


def _px(scan: Scan, word: Word) -> tuple[int, int, int, int] | None:
    """A word's box (page fractions) in the scan's pixels; None when it is not wholly
    on the scan (a caption beside it is never measured as part of it)."""
    rows, cols = scan.pixels.shape[:2]
    b = scan.box
    x, y = int((word.x - b["x"]) / b["w"] * cols), int((word.y - b["y"]) / b["h"] * rows)
    w, h = max(1, int(word.w / b["w"] * cols)), max(1, int(word.h / b["h"] * rows))
    return (x, y, w, h) if x >= 0 and y >= 0 and x + w <= cols and y + h <= rows else None
