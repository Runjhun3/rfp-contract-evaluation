"""What the document checks of a criterion check could and could not look at (D-063), in
plain words, so "nothing found" is never mistaken for "never checked". Worked out from
the pages themselves: scanned or born-digital, their resolution, and whether OCR kept
where each word is.
"""
from app.config import Settings
from app.schemas.records import Page

MIN_TEXT = 50             # characters of text layer worth checking on a born-digital page
SHOWN = 8                 # pages named before "and N more"


def coverage(page_nos: list[int], pages: dict[int, Page], scans: set[int],
             settings: Settings) -> str:
    """scans: the pages whose scan was found (the bid index's boxes)."""
    nos = sorted(n for n in set(page_nos) if n in pages)
    if not nos:
        return "No document page is cited, so no document was checked."
    scanned = [n for n in nos if n in scans]
    digital = [n for n in nos if n not in scans and len(pages[n].text.strip()) >= MIN_TEXT]
    worded = [n for n in scanned if pages[n].ocr_words]
    sharp = [n for n in worded if _dpi(pages[n]) >= settings.min_position_dpi]
    fine = [n for n in scanned if _dpi(pages[n]) >= settings.min_evidence_dpi]
    made = ["identifiers", "page numbering"] + (["stamp and signature reuse"] if scanned else [])
    made += ["near copies and letterheads"] if worded else []
    if digital or sharp:
        made.append(f"word positions on {_count(len(digital) + len(sharp))}")
    made += [f"pixels on {_count(len(fine))}"] if fine else []
    skipped = _skipped(scanned, worded, sharp, fine, settings)
    kinds = ", ".join(p for p in (scanned and f"{len(scanned)} scanned",
                                  digital and f"{len(digital)} born-digital") if p)
    return (f"Checked {_pages(nos)}{f' ({kinds})' if kinds else ''}: {', '.join(made)}."
            + (f" Not checked: {'; '.join(skipped)}." if skipped else ""))


def _skipped(scanned: list[int], worded: list[int], sharp: list[int], fine: list[int],
             settings: Settings) -> list[str]:
    skipped = []
    if len(worded) < len(scanned):
        skipped.append(f"word checks on {_count(len(scanned) - len(worded))} (OCR'd before "
                       "word positions were kept)")
    if len(sharp) < len(worded):
        skipped.append(f"word positions on {_count(len(worded) - len(sharp))} (scanned below "
                       f"{settings.min_position_dpi} dpi)")
    if len(fine) < len(scanned):
        skipped.append(f"pixels on {_count(len(scanned) - len(fine))} (scanned below "
                       f"{settings.min_evidence_dpi} dpi)")
    return skipped


def _dpi(page: Page) -> int:
    return page.image_dpi or 0


def _count(n: int) -> str:
    return f"{n} page" + ("" if n == 1 else "s")


def _pages(nos: list[int]) -> str:
    shown = ", ".join(map(str, nos[:SHOWN]))
    more = f" and {len(nos) - SHOWN} more" if len(nos) > SHOWN else ""
    return f"p.{shown}{more}"
