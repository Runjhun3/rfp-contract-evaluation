"""Label every page (type + the criterion it responds to, by MEANING) with the LLM, and
the eligibility requirements it is proof for.

Pages go in batches, in order. Each batch is shown the last pages of the one before
with the labels they were given, as context only (D-064): without them the first page
of a batch was labelled blind, so a new project starting there was taken for the one
before, or the second page of a certificate for a new project.

Evaluation and eligibility screening label a bid with the same criteria and
requirements, so the second one reuses the first one's replies (llm/client.py cache).
"""
from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.llm import PageLabel, PageLabels
from app.schemas.records import Criterion, Page, Requirement

BATCH_SIZE = 20
CONTEXT_PAGES = 3         # pages of the batch before, shown with their labels
SNIPPET_CHARS = 1500
SYSTEM = "You label pages of government tender bids. Return valid JSON only."
NO_PAGES_BEFORE = "(none: the first page under PAGES is the first page of the bid)"


def criteria_list(criteria: list[Criterion]) -> str:
    return "\n".join(f"{c.code} — {c.meaning}" + (" [whole bid]" if c.kind == "BID" else "")
                     for c in criteria)


def eligibility_list(requirements: list[Requirement]) -> str:
    return "\n".join(f"{r.code} — {r.meaning}" + (f" — proof: {r.proof}" if r.proof else "")
                     for r in requirements) or "(none)"


def label_pages(pages: list[Page], criteria: list[Criterion], llm: LlmClient,
                requirements: list[Requirement]) -> list[Page]:
    codes = {c.code for c in criteria}
    eligible = {r.code for r in requirements}
    for start in range(0, len(pages), BATCH_SIZE):
        batch = {p.pdf_page_no: p for p in pages[start:start + BATCH_SIZE]}
        before = pages[max(0, start - CONTEXT_PAGES):start]
        user = fill(load("label"), criteria_list=criteria_list(criteria),
                    eligibility_list=eligibility_list(requirements),
                    pages_before=_render(before, labelled=True) or NO_PAGES_BEFORE,
                    pages=_render(list(batch.values())))
        for label in llm.ask_json(SYSTEM, user, PageLabels).pages:
            if label.pdf_page_no in batch:          # never a page before: labelled already
                _apply(batch[label.pdf_page_no], label, codes, eligible)
    return pages


def _apply(page: Page, label: PageLabel, codes: set[str], eligible: set[str]) -> None:
    page.page_type = label.page_type
    page.criterion_code = label.criterion_code if label.criterion_code in codes else None
    page.map_confidence = label.map_confidence
    page.item_start = label.item_start
    page.title = label.title
    page.eligibility = [c for c in label.eligibility if c in eligible]


def _render(pages: list[Page], labelled: bool = False) -> str:
    """Page rows; labelled: with the label each was given (the pages before a batch)."""
    return "\n\n".join(f"[PDF p. {p.pdf_page_no}]{_label(p) if labelled else ''}\n"
                       f"{p.full_text()[:SNIPPET_CHARS]}" for p in pages)


def _label(page: Page) -> str:
    start = f", first page of: {page.title}" if page.item_start and page.title else ""
    return f" (labelled {page.page_type or 'OTHER'}{start})"
