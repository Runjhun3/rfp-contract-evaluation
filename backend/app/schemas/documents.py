"""What the AI reports about an item's documents beyond its facts, for Python to check:
disagreements between the firm's claims and its documents, documents referred to,
and stated totals or averages (evaluate/document_checks.py, stated_sums.py)."""
from pydantic import BaseModel, Field


class Fact(BaseModel):
    """A value with the page and exact words it comes from (used by every result)."""
    value: str | None = None
    page: int | None = None
    quote: str | None = None


class Discrepancy(BaseModel):
    """The firm's own page (claim table, project profile) and a document disagree.
    Both quotes are checked on their pages (evaluate/document_checks.py)."""
    about: str = ""                 # e.g. "contract value"
    claim: Fact | None = None       # what the firm's own page says
    document: Fact | None = None    # what the work order or certificate says


class Reference(BaseModel):
    """A document one of the item's documents refers to (e.g. "the extension letter
    dated 15.03.2022"); found_on_page: where it is among the item's pages, if it is."""
    document: str = ""
    page: int | None = None         # the page that refers to it
    quote: str | None = None        # the words that refer to it
    found_on_page: int | None = None


class StatedSum(BaseModel):
    """A total or average a document states, and the figures it is made of (fact names).
    Python recomputes it (evaluate/stated_sums.py)."""
    result: str                     # the fact holding the stated total or average
    op: str                         # "sum" or "average"
    parts: list[str] = Field(default_factory=list)
