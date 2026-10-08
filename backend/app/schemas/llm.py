"""Shapes the LLM must return. Every response is parsed into one of these."""
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.documents import Discrepancy, Fact, Reference, StatedSum


class Evidence(BaseModel):
    work_order: list[int] = Field(default_factory=list)
    completion_or_ca: list[int] = Field(default_factory=list)


class Job(BaseModel):
    """One row of a CV's employment record."""
    organisation: str = ""
    role: str = ""
    start: str | None = None      # "YYYY-MM"
    end: str | None = None        # "YYYY-MM" or "present"
    page: int | None = None
    quote: str | None = None


class SubScore(BaseModel):
    """One sub-criterion of a CV criterion, named as the RFP names it."""
    name: str
    marks: Decimal
    reason: str = ""


class CvFacts(BaseModel):
    degree: Fact | None = None
    stated_experience: Fact | None = None     # the total the CV itself states, if any
    employment: list[Job] = Field(default_factory=list)
    experience_years: Decimal | None = None   # total the LLM used for its decision
    facts: dict[str, Fact | None] = Field(default_factory=dict)   # other facts it relied on
    sub_scores: list[SubScore] = Field(default_factory=list)


class Condition(BaseModel):
    """One numeric or date test the LLM applied, in the RFP's own threshold, e.g.
    value_inr > 50000000. Python recomputes it (evaluate/condition_check.py)."""
    fact: str               # a fact name, "duration_months" or "experience_years"
    test: str               # > >= < <= =
    threshold: str          # plain number in the fact's unit, or YYYY-MM-DD
    met: bool


class HardFail(BaseModel):
    """Why an item is not eligible. Only these kinds are hard fails; a doubt about a
    category, type or relevance is a judgement call for the committee."""
    kind: str                       # missing_document | failed_test | rfp_exclusion
    detail: str = ""
    fact: str | None = None         # failed_test: the fact of the test in conditions
    rfp_quote: str | None = None    # rfp_exclusion: the RFP's words that exclude the item


class Recheck(BaseModel):
    """Set by Python, never by the LLM: the first answer, when a recomputed test
    disagreed and the item was sent back once."""
    first_eligible: bool
    first_marks: Decimal
    first_reason: str
    findings: list[str]


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
    conditions: list[Condition] = Field(default_factory=list)
    hard_fail: HardFail | None = None
    eligible: bool
    marks: Decimal
    reason: str
    confidence: float
    suspicious_text: list[Suspicious] = Field(default_factory=list)
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    sums: list[StatedSum] = Field(default_factory=list)
    recheck: Recheck | None = None

    def all_facts(self) -> dict[str, Fact | None]:
        facts = dict(self.facts)
        if self.cv:
            facts.update(self.cv.facts)
            facts["degree"] = self.cv.degree
            facts["stated_experience"] = self.cv.stated_experience
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
    title: str | None = None      # project name, or person + position, on item_start pages
    gem_bid_no: str | None = None
    eligibility: list[str] = Field(default_factory=list)   # requirements the page proves


class PageLabels(BaseModel):
    pages: list[PageLabel]


class EligibilityResult(BaseModel):
    """The AI's recommendation on one eligibility requirement for one bid."""
    code: str
    result: str                 # MET | NOT_MET | UNSURE
    finding: str
    facts: dict[str, Fact | None] = Field(default_factory=dict)
    conditions: list[Condition] = Field(default_factory=list)
    suspicious_text: list[Suspicious] = Field(default_factory=list)
    sums: list[StatedSum] = Field(default_factory=list)
