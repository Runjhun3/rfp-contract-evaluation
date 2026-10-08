"""One forensic finding: a region of a page that looks unlike the document around it,
how far it stands out (score: 1.0 = at the threshold), and why in plain words."""
from pydantic import BaseModel

from app.schemas.records import Word

# Words worth checking: those carrying a figure (a date, amount, number or reference).
MIN_DIGITS = 2


class Finding(BaseModel):
    kind: str                 # GEOMETRY, STAMP_REUSED, SIGNATURE_REUSED, NEAR_COPY, ...
    page: int
    region: dict[str, float]  # x, y, w, h as fractions of the page, from the top left
    score: float
    note: str
    crop: str | None = None   # path of its cropped image, for calibration (crops.py)


def is_figure(word: Word) -> bool:
    """A date, amount or number: mostly digits and the marks that join them; not a
    contents line's dot leader, nor a short whole number (a page or list number)."""
    text = word.text.strip("()[],;:")
    digits = sum(ch.isdigit() for ch in text)
    joined = sum(ch.isdigit() or ch in ".,/-:" for ch in text)
    if text.isdigit() and len(text) < 4:
        return False
    return digits >= MIN_DIGITS and joined >= 0.7 * len(text) and "..." not in text


def region(*words: Word, pad: float = 0.01) -> dict[str, float]:
    """The box around the words, padded a little so the crop shows their surroundings."""
    left = max(0.0, min(w.x for w in words) - pad)
    top = max(0.0, min(w.y for w in words) - pad)
    right = min(1.0, max(w.x + w.w for w in words) + pad)
    bottom = min(1.0, max(w.y + w.h for w in words) + pad)
    return {"x": left, "y": top, "w": right - left, "h": bottom - top}
