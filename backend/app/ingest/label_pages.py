"""Label every page (type + the criterion it responds to, by MEANING) with the LLM, and
the eligibility requirements it is proof for.

Evaluation and eligibility screening label a bid with the same criteria and
requirements, so the second one reuses the first one's replies (llm/client.py cache).
"""
from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.llm import PageLabels
from app.schemas.records import Criterion, Page, Requirement

BATCH_SIZE = 20
SNIPPET_CHARS = 1500
SYSTEM = "You label pages of government tender bids. Return valid JSON only."


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
    by_no = {p.pdf_page_no: p for p in pages}
    for start in range(0, len(pages), BATCH_SIZE):
        batch = pages[start:start + BATCH_SIZE]
        user = fill(load("label"), criteria_list=criteria_list(criteria),
                    eligibility_list=eligibility_list(requirements), pages=_render(batch))
        for label in llm.ask_json(SYSTEM, user, PageLabels).pages:
            page = by_no.get(label.pdf_page_no)
            if page is None:
                continue
            page.page_type = label.page_type
            page.criterion_code = label.criterion_code if label.criterion_code in codes else None
            page.map_confidence = label.map_confidence
            page.item_start = label.item_start
            page.title = label.title
            page.eligibility = [c for c in label.eligibility if c in eligible]
    return pages


def _render(batch: list[Page]) -> str:
    return "\n\n".join(f"[PDF p. {p.pdf_page_no}]\n{p.full_text()[:SNIPPET_CHARS]}"
                       for p in batch)
