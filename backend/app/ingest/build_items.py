"""Cut a labelled bid into items. Deterministic, no LLM.

An item starts on a page the labeller marked item_start (a project header or the
first page of a CV) and runs until the next item start or a section-level page
(claim summary, marketing). Each item belongs to exactly one criterion; a project
repeated under A.1, A.2 and A.3 becomes three items (copies).
"""
import unicodedata

from app.schemas.records import Item, Page

START_TYPES = {"PROJECT_HEADER", "CV"}
STOP_TYPES = {"CLAIM_SUMMARY", "MARKETING"}


def build_items(pages: list[Page]) -> list[Item]:
    items: list[Item] = []
    current: Item | None = None
    for page in pages:
        if page.item_start and page.page_type in START_TYPES:
            _close(items, current)
            current = _start(page)
        elif page.page_type in STOP_TYPES:
            _close(items, current)
            current = None
        elif current is not None:
            current.to_page = page.pdf_page_no
    _close(items, current)
    return items


def _start(page: Page) -> Item | None:
    if page.criterion_code is None:
        return None          # a project the bidder did not claim for any criterion
    return Item(
        label=f"{page.criterion_code} p.{page.pdf_page_no}",
        title=_title(page),
        kind="CV" if page.page_type == "CV" else "PROJECT",
        criterion_code=page.criterion_code,
        map_confidence=page.map_confidence or 0.0,
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
