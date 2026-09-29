"""Cut a labelled bid into items. Deterministic, no LLM.

An item starts on a page the labeller marked item_start (a project header or the
first page of a CV) and runs until the next item start or a section-level page
(claim summary, marketing). Each item belongs to exactly one criterion; a project
repeated under A.1, A.2 and A.3 becomes three items (copies).

Which criterion: the bidder's claim decides.
- A CV names the position it is proposed for, so a CV page's own label decides.
- A project page usually does not say which criterion it is claimed under, so a
  claim summary for ONE criterion (itself mapped by meaning) opens a section, and
  every project that follows belongs to it until the next claim summary or
  marketing page. A summary spread over consecutive pages is one summary: it opens
  a section only when all its pages point to the same criterion (a page labelled
  with no criterion means the summary covers several).
- Otherwise an item falls back to its own page's meaning-based label.
- A criterion scored on the whole bid (kind BID, e.g. turnover) gets one item: every
  page the labeller tagged as its evidence, wherever it sits.

The same person's CV found twice under one criterion (e.g. a full CV and a one-page
profile) is one CV: the longest copy is scored, the others are marked duplicate_of.
"""
import re
import unicodedata

from app.schemas.records import Item, Page

START_TYPES = {"PROJECT_HEADER", "CV"}
STOP_TYPES = {"CLAIM_SUMMARY", "MARKETING"}


def build_items(pages: list[Page], kinds: dict[str, str]) -> list[Item]:
    """kinds: criterion code -> "PROJECT" | "CV" | "BID", for the criteria being scored."""
    items: list[Item] = []
    current: Item | None = None
    section: Page | None = None
    summary: list[Page] = []           # consecutive claim-summary pages seen so far
    for page in pages:
        summary = summary + [page] if page.page_type == "CLAIM_SUMMARY" else []
        if page.item_start and page.page_type in START_TYPES:
            _close(items, current)
            current = _start(page, section, kinds)
        elif page.page_type in STOP_TYPES:
            _close(items, current)
            current = None
            codes = {p.criterion_code for p in summary}
            section = page if len(codes) == 1 and None not in codes else None
        elif current is not None:
            current.to_page = page.pdf_page_no
    _close(items, current)
    return mark_duplicate_cvs(items) + whole_bid_items(pages, kinds)


def whole_bid_items(pages: list[Page], kinds: dict[str, str]) -> list[Item]:
    """One item per criterion scored on the whole bid (kind BID): every page the
    labeller tagged as evidence for it, wherever it sits in the bid."""
    items = []
    for code in (c for c, kind in kinds.items() if kind == "BID"):
        mine = [p for p in pages if p.criterion_code == code]
        if not mine:
            continue                  # nothing found: the criterion is flagged NO_ITEMS_FOUND
        first, last = mine[0].pdf_page_no, mine[-1].pdf_page_no
        items.append(Item(label=f"{code} p.{first}-{last}", title=f"Evidence for {code}",
                          kind="BID", criterion_code=code,
                          map_confidence=min(p.map_confidence or 0.0 for p in mine),
                          from_page=first, to_page=last, pages=[p.pdf_page_no for p in mine]))
    return items


def mark_duplicate_cvs(items: list[Item]) -> list[Item]:
    """Match CVs by the person the labeller named; keep the longest copy, the first
    on a tie. A CV without a labelled name is never matched."""
    kept: dict[tuple[str, str], Item] = {}
    for item in sorted(items, key=lambda i: -(i.to_page - i.from_page)):
        if item.kind != "CV" or not item.person:
            continue
        key = (item.criterion_code, item.person)
        if key in kept:
            item.duplicate_of = kept[key].label
        else:
            kept[key] = item
    return items


def _person(page: Page) -> str:
    """The name part of the labeller's "name, position" title, letters only."""
    if page.page_type != "CV" or not page.title:
        return ""
    return re.sub(r"[\W_]", "", page.title.split(",")[0].casefold())


def _start(page: Page, section: Page | None, kinds: dict[str, str]) -> Item | None:
    kind = "CV" if page.page_type == "CV" else "PROJECT"
    own_cv = kind == "CV" and kinds.get(page.criterion_code) == "CV"
    in_section = section is not None and kinds.get(section.criterion_code) == kind
    source = section if in_section and not own_cv else page
    if source.criterion_code not in kinds:
        return None          # a project the bidder did not claim for any scored criterion
    return Item(
        label=f"{source.criterion_code} p.{page.pdf_page_no}",
        title=page.title or _title(page),
        person=_person(page),
        kind=kind,
        criterion_code=source.criterion_code,
        map_confidence=source.map_confidence or 0.0,
        from_page=page.pdf_page_no,
        to_page=page.pdf_page_no,
    )


def _close(items: list[Item], current: Item | None) -> None:
    if current is not None:
        current.label = f"{current.criterion_code} p.{current.from_page}-{current.to_page}"
        items.append(current)


def _title(page: Page) -> str:
    """First line that reads like a heading: several words, not a footer."""
    for raw in page.full_text().splitlines():
        line = "".join(ch for ch in raw if unicodedata.category(ch)[0] != "C").strip()
        if "©" in line or sum(w.isalpha() for w in line.split()) < 3:
            continue
        return line[:160]
    return ""
