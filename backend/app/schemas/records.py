"""Records the pipeline writes. Field names follow docs/schema.md."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

Kind = Literal["PROJECT", "CV", "BID"]   # BID: scored once on the whole bid


class RunContext(BaseModel):
    tender_no: str
    department: str
    bidder: str
    bid_due_date: date


class CountBand(BaseModel):
    """Marks for a number of qualifying items: min..max items (max None = or more)."""
    min: int
    max: int | None = None
    marks: Decimal


class Criterion(BaseModel):
    code: str
    title: str
    meaning: str
    kind: Kind
    rfp_text: str = ""
    max_marks: Decimal
    max_items: int | None = None
    allowed_item_marks: list[Decimal]
    count_bands: list[CountBand] = []     # marks by number of qualifying items


class Page(BaseModel):
    pdf_page_no: int
    text: str
    image_ratio: float = 0.0
    ocr_text: str | None = None
    extraction: Literal["TEXT_LAYER", "TEXTRACT", "TESSERACT"] = "TEXT_LAYER"
    ocr_confidence: float | None = None
    page_type: str | None = None
    criterion_code: str | None = None
    map_confidence: float | None = None
    item_start: bool = False
    title: str | None = None

    def full_text(self) -> str:
        if not self.ocr_text:
            return self.text
        return f"{self.text}\n[OCR]\n{self.ocr_text}"


class Item(BaseModel):
    """One project section or CV, under exactly one criterion."""
    label: str
    title: str
    kind: Kind
    criterion_code: str
    map_confidence: float
    from_page: int
    to_page: int
    pages: list[int] = []             # BID: the evidence pages (not a continuous range)
    person: str = ""                  # CV: the proposed person's name, normalised
    duplicate_of: str | None = None   # label of the item kept for the same CV; not scored

    def page_list(self) -> list[int]:
        """The item's pages: its evidence pages (BID), else its continuous range."""
        return self.pages or list(range(self.from_page, self.to_page + 1))


class EvidenceCheck(BaseModel):
    label: str
    fact: str
    pdf_page_no: int | None = None
    quote: str | None = None
    quote_found: bool
    match_score: int = 0
    parsed_value: str | None = None
    value_matches: bool | None = None   # None = value not checkable (e.g. client name)
    note: str = ""

    def passed(self) -> bool:
        return self.quote_found and self.value_matches is not False


class CopyGroup(BaseModel):
    labels: list[str]
    mismatches: list[str]


class ArithmeticCheck(BaseModel):
    code: str
    llm_marks: Decimal
    checked_marks: Decimal
    ok: bool
    issues: list[str]


class CriterionScore(BaseModel):
    code: str
    llm_marks: Decimal
    checked_marks: Decimal
    arithmetic_ok: bool
    needs_review: bool
    review_reasons: list[str]
    summary: str
