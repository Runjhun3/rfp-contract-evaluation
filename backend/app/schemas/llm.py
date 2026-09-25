"""Shapes the LLM must return. Every response is parsed into one of these."""
from decimal import Decimal

from pydantic import BaseModel, Field


class Fact(BaseModel):
    value: str | None = None
    page: int | None = None
    quote: str | None = None


class Evidence(BaseModel):
    work_order: list[int] = Field(default_factory=list)
    completion_or_ca: list[int] = Field(default_factory=list)


class CvFacts(BaseModel):
    degree: Fact | None = None
    years_experience: Fact | None = None
    sports_or_govt_experience: Fact | None = None
    sub_marks: dict[str, Decimal] = Field(default_factory=dict)


class Suspicious(BaseModel):
    page: int | None = None
    quote: str = ""


class ItemResult(BaseModel):
    label: str
    code: str
    facts: dict[str, Fact | None] = Field(default_factory=dict)
    evidence: Evidence = Field(default_factory=Evidence)
    cv: CvFacts | None = None
    relies_on: list[str] = Field(default_factory=list)
    eligible: bool
    marks: Decimal
    reason: str
    confidence: float
    suspicious_text: list[Suspicious] = Field(default_factory=list)

    def all_facts(self) -> dict[str, Fact | None]:
        facts = dict(self.facts)
        if self.cv:
            facts["degree"] = self.cv.degree
            facts["years_experience"] = self.cv.years_experience
            facts["sports_or_govt_experience"] = self.cv.sports_or_govt_experience
        return facts


class CriterionItem(BaseModel):
    label: str
    order: int
    eligible: bool
    counted: bool
    marks: Decimal
    reason: str


class CriterionResult(BaseModel):
    code: str
    items: list[CriterionItem]
    counted_items: int
    marks: Decimal
    summary: str


class PageLabel(BaseModel):
    pdf_page_no: int
    page_type: str
    criterion_code: str | None = None
    map_confidence: float | None = None
    item_start: bool = False
    gem_bid_no: str | None = None


class PageLabels(BaseModel):
    pages: list[PageLabel]
