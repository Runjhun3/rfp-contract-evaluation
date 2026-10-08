"""Basic checks on the documents behind an item, for the committee (decisions.md D-057).
Each raises a flag and corrects nothing; all work within the one bid:
  - date order (date_order.py) and stated totals or averages (stated_sums.py),
  - the firm's own page disagreeing with a document: both quotes must be on their pages,
  - a document an item's document refers to but that is not among its pages,
  - evidence read from a scan too low in resolution to trust (Page.image_dpi),
  - the document checks of the evidence pages (document_flags.py, D-059, D-062, D-063).
"""
from datetime import date

from app.config import Settings
from app.evaluate.date_order import DATE_ORDER, date_order
from app.evaluate.evidence_check import check_fact
from app.evaluate.quote_match import quote_score
from app.evaluate.stated_sums import STATED_SUM, stated_sums
from app.schemas.llm import ItemResult
from app.schemas.records import EvidenceCheck, Item, Page

IDENTIFIER = "document identifier"
FORENSIC = "document forensics"
CLAIM = "claim vs documents"
REFERENCE = "referenced document"
RESOLUTION = "image resolution"
COVERAGE = "document checks made"
# Each check's review reason (docs/pipeline.md), raised when it finds a problem.
REASONS = {DATE_ORDER: "DATE_ORDER", STATED_SUM: "STATED_SUM", CLAIM: "CLAIM_DIFFERS",
           REFERENCE: "REFERENCE_MISSING", RESOLUTION: "LOW_RESOLUTION",
           IDENTIFIER: "DOCUMENT_ID", FORENSIC: "DOCUMENT_FLAG"}
DOCUMENT_FLAGS = (IDENTIFIER, FORENSIC)


def document_checks(result: ItemResult, item: Item, pages: dict[int, Page],
                    settings: Settings, as_of: date) -> list[EvidenceCheck]:
    return (date_order(result, item, pages, settings, as_of)
            + stated_sums(result.label, result.sums, result.all_facts(), settings)
            + [_claim(result.label, d, item, pages, settings) for d in result.discrepancies]
            + _references(result, item, pages, settings)
            + low_resolution(result.label, cited_pages(result, item), pages, settings))


def low_resolution(label: str, cited: list[int], pages: dict[int, Page],
                   settings: Settings) -> list[EvidenceCheck]:
    """One flag naming the cited pages scanned below the minimum resolution."""
    low = [(n, pages[n].image_dpi) for n in sorted(set(cited))
           if n in pages and pages[n].image_dpi and pages[n].image_dpi < settings.min_evidence_dpi]
    if not low:
        return []
    shown = ", ".join(f"p.{n} (about {dpi} dpi)" for n, dpi in low)
    return [EvidenceCheck(label=label, fact=RESOLUTION, quote_found=True, value_matches=False,
                          pdf_page_no=low[0][0],
                          note=f"Scanned too low to read reliably: {shown}. Check the figures "
                               "read from these pages against the page itself.")]


def cited_pages(result: ItemResult, item: Item) -> list[int]:
    """The item's evidence pages: those cited as the RFP's proof and those its facts
    are quoted from (D-059: the documents the criteria ask for)."""
    facts = [f.page for f in result.all_facts().values() if f and f.page]
    cited = result.evidence.work_order + result.evidence.completion_or_ca + facts
    return [n for n in cited if n in item.page_list()]


def _claim(label: str, d, item: Item, pages: dict[int, Page],
           settings: Settings) -> EvidenceCheck:
    """The firm's page may sit anywhere in the bid (a claim table often comes before the
    item); the document must be one of the item's pages."""
    base = {"label": label, "fact": CLAIM, "quote_found": True}
    claim_found = d.claim and _on_page(d.claim.quote, d.claim.page, pages, settings)
    doc_found = d.document and check_fact(item, CLAIM, d.document, pages, settings).quote_found
    if not (claim_found and doc_found):
        return EvidenceCheck(**base, note=f"A difference about {d.about or 'a fact'} was "
                                          "reported, but its quotes were not found on the "
                                          "pages; please check it.")
    return EvidenceCheck(**base, value_matches=False, pdf_page_no=d.document.page,
                         quote=d.document.quote,
                         note=f"{(d.about or 'A fact').capitalize()}: the firm's page says "
                              f"\"{d.claim.value}\" (p.{d.claim.page}), the document says "
                              f"\"{d.document.value}\" (p.{d.document.page}).")


def _references(result: ItemResult, item: Item, pages: dict[int, Page],
                settings: Settings) -> list[EvidenceCheck]:
    """A flag for each document referred to that is not among the item's pages; the
    words that refer to it must be on their page."""
    checks = []
    for r in result.references:
        if r.found_on_page in item.page_list() or r.page not in pages or not r.quote:
            continue
        if not _on_page(r.quote, r.page, pages, settings):
            continue
        checks.append(EvidenceCheck(
            label=result.label, fact=REFERENCE, quote_found=True, value_matches=False,
            pdf_page_no=r.page, quote=r.quote,
            note=f"p.{r.page} refers to {r.document or 'another document'}, which is not "
                 "among this item's pages."))
    return checks


def _on_page(quote: str | None, page: int | None, pages: dict[int, Page],
             settings: Settings) -> bool:
    if not quote or page not in pages:
        return False
    return quote_score(quote, pages[page].full_text()) >= settings.quote_match_threshold
