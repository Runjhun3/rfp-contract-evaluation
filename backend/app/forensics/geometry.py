"""Word-position checks (D-058, D-061): a figure (date, amount, number) that does not
sit like its words, as one typed over or pasted in often does not: off their baseline,
taller or shorter, overlapping a word, on a line tilted from the page's, or (text layer)
in another font or size or unevenly spaced. Each word is compared only with its run:
its line up to a wide gap, so table cells and columns are measured apart (and curved
photos tolerated). Left out: headers and footers, handwriting and words OCR is unsure of
(unreliable boxes); fonts and sizes are compared only on body-text lines, not callouts.
Scans: from MIN_POSITION_DPI (D-060), looser limits. Calibrated; a finding is a flag.
"""
import re
from statistics import median

from app.forensics.finding import Finding, is_figure, region
from app.forensics.lines import MIN_LINE, angle, baseline_at, group_lines, page_tilt, runs
from app.schemas.records import Word

LIMITS = {"baseline": 0.35, "height": 1.4, "overlap": 0.25, "skew": 1.5, "size": 0.08,
          "spacing": 0.35}
SCAN = {"baseline": 0.5, "height": 1.6, "skew": 2.5}    # a scanned printout wobbles
DESIGN = 0.4             # a size this far from its line's is a designed callout, not an edit
MIN_CONF = 0.7           # OCR confidence below which a word's box is not trusted
MARGIN = 0.06            # the top and bottom bands of a page: headers, footers, numbers
_SUBSET = re.compile(r"^[A-Z]{6}\+")
_STYLE = re.compile(r"[-,]?(Bold|Italic|Oblique|Regular|Light|Medium|Semibold|SemiBold|"
                    r"Black|Book|Condensed|Narrow|MT|PS)+$", re.I)


def check_words(words: list[Word], page: int, digital: bool) -> list[Finding]:
    """The figures on one page that stand out from their line."""
    limits = LIMITS if digital else {**LIMITS, **SCAN}
    kept = [w for w in words if MARGIN < w.y + w.h / 2 < 1 - MARGIN and _trusted(w)]
    lines = [run for line in group_lines(kept) for run in runs(line)]
    tilt = page_tilt(lines)
    body = _body_size(words) if digital else None
    found = []
    for line in (l for l in lines if len(l) >= MIN_LINE):
        tilted = tilt is not None and abs(angle(line) - tilt) > limits["skew"]
        typed = body is not None and abs(median(w.size or 0 for w in line) - body) < 0.5
        for word in (w for w in line if is_figure(w)):
            reasons = _reasons(word, [w for w in line if w is not word], typed, limits)
            if tilted:
                reasons.append((abs(angle(line) - tilt) / limits["skew"],
                                f"its line is tilted {abs(angle(line) - tilt):.1f}° "
                                "from the rest of the page"))
            if reasons:
                found.append(Finding(kind="GEOMETRY", page=page, region=region(word),
                                     score=max(s for s, _ in reasons),
                                     note=f"\"{word.text}\": " + "; ".join(r for _, r in reasons)))
    return found


def _trusted(word: Word) -> bool:
    """Printed and read with confidence (a text layer's words always are)."""
    return not word.handwritten and (word.conf is None or word.conf >= MIN_CONF)


def _reasons(word: Word, others: list[Word], typed: bool,
             limits: dict) -> list[tuple[float, str]]:
    """typed: a body-text line of a text layer, where fonts and sizes are compared."""
    sizes = [w.size for w in others if w.size]
    if typed and word.size and sizes and abs(word.size / median(sizes) - 1) > DESIGN:
        return []
    found = []
    tall = [w for w in others if is_figure(w) or any(c.isupper() for c in w.text)]
    height = median(w.h for w in tall) if len(tall) >= 2 else None
    if height:
        drift = abs(word.y + word.h - baseline_at(tall, others, word.x + word.w / 2)) / height
        if drift > limits["baseline"]:
            found.append((drift / limits["baseline"], "it sits off the line's baseline"))
        ratio = max(word.h / height, height / word.h)
        if ratio > limits["height"]:
            found.append((ratio / limits["height"], "its height differs from its line's"))
    found += _overlap(word, others)
    return found + (_type(word, others) if typed else [])


def _overlap(word: Word, others: list[Word]) -> list[tuple[float, str]]:
    for other in others:
        dx = min(word.x + word.w, other.x + other.w) - max(word.x, other.x)
        dy = min(word.y + word.h, other.y + other.h) - max(word.y, other.y)
        share = max(dx, 0) * max(dy, 0) / max(min(word.w * word.h, other.w * other.h), 1e-9)
        if share > LIMITS["overlap"]:
            return [(share / LIMITS["overlap"], f"it overlaps \"{other.text}\"")]
    return []


def _type(word: Word, others: list[Word]) -> list[tuple[float, str]]:
    """Text layer only: the font, size and letter spacing of the figure."""
    found = []
    families = [_family(w.font) for w in others if w.font]
    if families and _family(word.font) not in families:
        found.append((2.0, f"its font ({_family(word.font)}) is not used elsewhere on its line"))
    sizes = [w.size for w in others if w.size]
    if sizes and word.size and abs(word.size - median(sizes)) / median(sizes) > LIMITS["size"]:
        found.append((abs(word.size - median(sizes)) / median(sizes) / LIMITS["size"],
                      f"its size ({word.size}) differs from its line's ({median(sizes)})"))
    if word.spacing and word.spacing > LIMITS["spacing"]:
        found.append((word.spacing / LIMITS["spacing"], "its letters are unevenly spaced"))
    return found


def _body_size(words: list[Word]) -> float | None:
    """The page's body text size: the size most of its words are set in."""
    sizes = [round(w.size, 1) for w in words if w.size]
    return max(set(sizes), key=sizes.count) if sizes else None


def _family(font: str | None) -> str:
    return _STYLE.sub("", _SUBSET.sub("", font or ""))

