"""Layout checks on a criterion's evidence pages, within one bid (D-059), reading only
the words inside each page's scan (not the bidder's captions around it):
  - near copy: another scan with almost the same words but other dates or amounts (a
    letter reused as a template). Not flagged: OCR reading one document two ways (a
    letter for a digit, a stray letter), only reference numbers differing (a genuine
    series of orders), or boilerplate with one change;
  - missing page: pages printing "Page 1 of 4", "Page 2 of 4" and "Page 4 of 4" next to
    each other, but no page 3 between them (a first or last page often prints no
    number, or OCR misses it: only a gap inside the run counts);
  - odd page: among the evidence pages under one letterhead (read from the top of each
    scan), one whose text size or margin differs sharply from the others.
"""
import re
from statistics import median

from app.forensics.finding import Finding, is_figure
from app.schemas.records import Word

SAME_WORDS = 0.85         # share of words two scans have in common to be near copies
MIN_WORDS = 40
GROUP = 0.6               # letterhead words in common to be the same issuer
HEAD = 0.15               # the top of a scan holding its letterhead
WHOLE = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
_DATE = re.compile(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}")
_AMOUNT = re.compile(r"(₹|rs\.?|inr)|\d{1,3}(,\d{2,3})+|\d+\.\d{2}$", re.I)
_PAGE_OF = re.compile(r"page\s*(\d{1,3})\s*(?:of|/)\s*(\d{1,3})", re.I)

Scanned = dict[int, list[Word]]    # each scan's words, placed as fractions of the scan


def near_copy(page: int, scanned: Scanned, same_scan) -> Finding | None:
    """same_scan(a, b): the two pages are one scan shown twice (not a copy)."""
    if len(scanned.get(page, [])) < MIN_WORDS:
        return None
    words, figures = _words(scanned[page]), _figures(scanned[page])
    for other, its in sorted(scanned.items()):
        if other == page or len(its) < MIN_WORDS or same_scan(page, other):
            continue
        shared = len(words & _words(its)) / max(1, len(words | _words(its)))
        changed = _material(figures, _figures(its))
        if shared >= SAME_WORDS and changed:
            return Finding(kind="NEAR_COPY", page=page, region=WHOLE, score=shared / SAME_WORDS,
                           note=f"Almost the same words as p.{other} ({shared:.0%}) but "
                                "other dates or amounts: " + ", ".join(changed[:6]) + ".")
    return None


def missing_pages(page: int, texts: dict[int, str]) -> Finding | None:
    """texts: every page's text (text layer and OCR)."""
    shown = _PAGE_OF.search(texts.get(page, ""))
    if not shown or not 2 <= int(shown[2]) <= 50:
        return None
    total = int(shown[2])
    near = range(page - total, page + total + 1)
    found = {int(m[1]) for n in near if (m := _PAGE_OF.search(texts.get(n, "")))
             and int(m[2]) == total}
    missing = sorted(set(range(min(found), max(found) + 1)) - found)
    if not missing:
        return None
    return Finding(kind="PAGE_MISSING", page=page, region=WHOLE, score=1.0,
                   note=f"It prints page {shown[1]} of {total}; next to it are pages "
                        f"{', '.join(map(str, sorted(found)))} but not "
                        f"{', '.join(map(str, missing))}.")


def odd_pages(pages: list[int], scanned: Scanned) -> list[Finding]:
    """Among the given evidence pages, one unlike the others under its letterhead."""
    groups: list[list[int]] = []
    for p in (p for p in pages if len(scanned.get(p, [])) >= MIN_WORDS):
        head = _head(scanned[p])
        group = next((g for g in groups if _jaccard(head, _head(scanned[g[0]])) >= GROUP),
                     None)
        group.append(p) if group else groups.append([p])
    found = []
    for group in (g for g in groups if len(g) >= 3):
        size = median(_size(scanned[p]) for p in group)
        margin = median(_margin(scanned[p]) for p in group)
        found += [Finding(kind="ODD_PAGE", page=p, region=WHOLE, score=1.0,
                          note=f"Its text size or margin differs from the {len(group) - 1} "
                               "other pages under the same letterhead.")
                  for p in group if abs(_size(scanned[p]) / size - 1) > 0.25
                  or abs(_margin(scanned[p]) - margin) > 0.05]
    return found


def _material(a: set[str], b: set[str]) -> list[str]:
    """The dates and amounts that differ, leaving out OCR noise (one character apart,
    or the same digits with stray letters); boilerplate (under 3) needs two changes."""
    only_a, only_b = a - b, b - a
    noise = {x for x in only_a for y in only_b if _digits(x) == _digits(y) or _near(x, y)}
    noise |= {y for y in only_b for x in only_a if _digits(x) == _digits(y) or _near(x, y)}
    changed = sorted(f for f in (only_a | only_b) - noise if _DATE.search(f) or _AMOUNT.search(f))
    counted = [f for f in a | b if _DATE.search(f) or _AMOUNT.search(f)]
    return changed if len(changed) >= (1 if len(counted) >= 3 else 2) else []


def _near(x: str, y: str) -> bool:
    """OCR reading one figure two ways: one character apart where it is not one digit
    for another (O for 0, a dropped letter). A digit changed to another digit (2021 to
    2023) is exactly the edit worth seeing, so it is never noise."""
    if len(x) == len(y):
        diff = [(a, b) for a, b in zip(x, y) if a != b]
        return len(diff) == 1 and not (diff[0][0].isdigit() and diff[0][1].isdigit())
    if abs(len(x) - len(y)) != 1:
        return False
    short, long = sorted((x, y), key=len)
    return any(long[:i] + long[i + 1:] == short and not long[i].isdigit()
               for i in range(len(long)))


def _digits(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit() or ch in ".,/-")


def _words(words: list[Word]) -> set[str]:
    return {w.text.lower() for w in words if not is_figure(w) and len(w.text) > 2}


def _figures(words: list[Word]) -> set[str]:
    """Every token with two digits or more: OCR's stray letters must not hide a figure
    from its twin on the other page (only dates and amounts can count as changed)."""
    return {w.text.strip(".,;:()") for w in words if sum(c.isdigit() for c in w.text) >= 2}


def _head(words: list[Word]) -> set[str]:
    return {w.text.lower() for w in words if w.y < HEAD and w.text.isalpha()
            and len(w.text) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _size(words: list[Word]) -> float:
    return median(w.h for w in words)


def _margin(words: list[Word]) -> float:
    return min(w.x for w in words)
