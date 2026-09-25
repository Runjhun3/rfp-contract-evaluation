"""EXTRACT_CRITERIA: read the RFP and turn its eligibility/evaluation clauses into
criterion rows (by meaning, wherever they sit), plus a draft criteria block for
the human to check and approve.
"""
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field

from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.records import Page

CHUNK_PAGES = 40
SYSTEM = "You extract evaluation criteria from government RFPs. Return valid JSON only."


class ExtractedCriterion(BaseModel):
    code: str
    parent: str | None = None
    stage: str
    title: str
    rfp_text: str
    meaning: str
    max_marks: str | None = None
    max_items: int | None = None
    kind: str | None = None
    item_marks: list[str] = Field(default_factory=list)
    scored_by: str = "LLM"
    rfp_page: int | None = None


class Extracted(BaseModel):
    criteria: list[ExtractedCriterion]


def extract(pages: list[Page], llm: LlmClient) -> list[ExtractedCriterion]:
    found: dict[str, ExtractedCriterion] = {}
    for start in range(0, len(pages), CHUNK_PAGES):
        chunk = pages[start:start + CHUNK_PAGES]
        text = "\n\n".join(f"[PDF p. {p.pdf_page_no}]\n{p.full_text()}" for p in chunk)
        for c in llm.ask_json(SYSTEM, fill(load("criteria"), pages=text), Extracted).criteria:
            found.setdefault(c.code, c)
    return list(found.values())


def decimal_or_none(value: str | None) -> Decimal | None:
    try:
        return Decimal(str(value)) if value not in (None, "") else None
    except InvalidOperation:
        return None


def build_block(rows: list[dict]) -> str:
    """Draft rule text for the prompt, from the criterion rows the LLM scores."""
    parts = ["Apply each criterion exactly as the RFP text says. "
             "The plain-words line only explains it."]
    for c in rows:
        if c["stage"] != "TECHNICAL" or c["scored_by"] != "LLM":
            continue
        limit = f", max {c['max_items']} items" if c.get("max_items") else ""
        allowed = c.get("allowed") or "as the RFP text says"
        parts.append(f"CRITERION {c['code']}  (max {c['max_marks']} marks{limit})\n"
                     f"RFP text: \"{c['rfp_text']}\"\n"
                     f"In plain words: {c['meaning']}\n"
                     f"Marks one item can earn: {allowed}")
    return "\n\n".join(parts)
