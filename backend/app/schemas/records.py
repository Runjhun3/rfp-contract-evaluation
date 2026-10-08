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


class Requirement(BaseModel):
    """One eligibility requirement (pass/fail), with the proof the RFP asks for."""
    criterion_id: str
    code: str
    title: str
    meaning: str
    rfp_text: str = ""
    proof: str | None = None


class Word(BaseModel):
    """One word and where it is on its page: x, y, w, h as fractions of the page width
    and height from the top left. conf: OCR confidence 0-1 (None for a text layer);
    font and size: from a text layer only."""
    text: str
    x: float
    y: float
    w: float
    h: float
    conf: float | None = None
    font: str | None = None
    size: float | None = None
    spacing: float | None = None          # text layer: unevenness of its letter gaps (0 even)
    handwritten: bool | None = None       # Textract: written by hand (None: not known)


class Page(BaseModel):
    pdf_page_no: int
    text: str
    image_ratio: float = 0.0
    image_dpi: int | None = None          # effective resolution of its largest scanned image
    ocr_text: str | None = None
    extraction: Literal["TEXT_LAYER", "TEXTRACT", "TESSERACT"] = "TEXT_LAYER"
    ocr_confidence: float | None = None
    ocr_words: list[Word] = []            # OCR words with their boxes (document checks)
    page_type: str | None = None
    criterion_code: str | None = None
    map_confidence: float | None = None
    item_start: bool = False
    title: str | None = None
    eligibility: list[str] = []           # codes of the eligibility requirements it proves

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
    region: dict[str, float] | None = None   # a forensic finding's box: x, y, w, h (0-1)

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
