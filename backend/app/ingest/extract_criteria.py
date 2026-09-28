"""EXTRACT_CRITERIA: read the RFP and turn its eligibility/evaluation clauses into
criterion rows (by meaning, wherever they sit), plus the general conditions that
apply to several criteria, and a draft criteria block for the human to approve.
"""
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field

from app.criteria import group_codes
from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.records import Page

CHUNK_PAGES = 100   # whole RFP in one call up to 100 pages (docs/pipeline.md), so
                    # a form at the back is seen next to the criterion it proves
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


class GeneralCondition(BaseModel):
    text: str
    rfp_page: int | None = None


class Extracted(BaseModel):
    criteria: list[ExtractedCriterion]
    general_conditions: list[GeneralCondition] = Field(default_factory=list)


def extract(pages: list[Page], llm: LlmClient) -> Extracted:
    rows: list[ExtractedCriterion] = []
    general: dict[str, GeneralCondition] = {}
    for start in range(0, len(pages), CHUNK_PAGES):
        chunk = pages[start:start + CHUNK_PAGES]
        text = "\n\n".join(f"[PDF p. {p.pdf_page_no}]\n{p.full_text()}" for p in chunk)
        answer = llm.ask_json(SYSTEM, fill(load("criteria"), pages=text), Extracted)
        rows += answer.criteria
        for g in answer.general_conditions:
            general.setdefault(" ".join(g.text.split()), g)
    return Extracted(criteria=merge(rows), general_conditions=list(general.values()))


def merge(rows: list[ExtractedCriterion]) -> list[ExtractedCriterion]:
    """One row per code across chunks. Eligibility rows are renumbered E.1, E.2 ... in
    the order found, so two chunks that both start at E.1 do not overwrite each other;
    the same eligibility title found twice is kept once."""
    scored: dict[str, ExtractedCriterion] = {}
    eligibility: dict[str, ExtractedCriterion] = {}
    for c in rows:
        if c.stage == "ELIGIBILITY":
            eligibility.setdefault(" ".join(c.title.lower().split()), c)
        else:
            scored.setdefault(c.code, c)
    for n, c in enumerate(eligibility.values(), start=1):
        c.code, c.parent = f"E.{n}", None
    return [*eligibility.values(), *scored.values()]


def decimal_or_none(value: str | None) -> Decimal | None:
    try:
        return Decimal(str(value)) if value not in (None, "") else None
    except InvalidOperation:
        return None


def build_block(rows: list[dict], general: list[GeneralCondition] | None = None) -> str:
    """Draft rule text for the prompt: the RFP's general conditions, then every
    criterion the LLM scores per project/CV.

    Group headings are left out: their marks are only the sum of their sub-criteria.
    """
    groups = group_codes(rows)
    parts = ["Apply each criterion exactly as the RFP text says. "
             "The plain-words line only explains it."]
    if general:
        parts.append("GENERAL CONDITIONS (apply to every criterion below)\n" + "\n".join(
            f"- \"{g.text}\"" + (f" [RFP p. {g.rfp_page}]" if g.rfp_page else "")
            for g in general))
    for c in rows:
        if (c["stage"] != "TECHNICAL" or c["scored_by"] != "LLM" or not c["kind"]
                or c["code"] in groups):
            continue
        limit = f", max {c['max_items']} items" if c.get("max_items") else ""
        allowed = c.get("allowed") or "as the RFP text says"
        parts.append(f"CRITERION {c['code']}  (max {c['max_marks']} marks{limit})\n"
                     f"RFP text: \"{c['rfp_text']}\"\n"
                     f"In plain words: {c['meaning']}\n"
                     f"Marks one item can earn: {allowed}")
    return "\n\n".join(parts)
