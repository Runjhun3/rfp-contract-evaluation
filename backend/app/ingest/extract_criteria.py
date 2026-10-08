"""EXTRACT_CRITERIA: read the RFP and turn its eligibility/evaluation clauses into
criterion rows (by meaning, wherever they sit), plus the general conditions that
apply to several criteria, and a draft criteria block for the human to approve.
"""
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field

from app.criteria import scoring
from app.evaluate.count_bands import describe
from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.records import CountBand, Page

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
    count_bands: list[dict] = Field(default_factory=list)   # {"min", "max", "marks"}
    proof: str | None = None       # eligibility: the documents the RFP asks for as proof
    rfp_no: str | None = None      # screened rows: the number the RFP prints ("3", "B")
    source_reference: str | None = None
    classification_unsure: bool = False
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
    merged = merge(rows)
    if not any(c.stage in ("TECHNICAL", "PRESENTATION") for c in merged):
        raise ValueError("Extraction returned no scored criteria; review the RFP extraction.")
    return Extracted(criteria=merged, general_conditions=list(general.values()))


def merge(rows: list[ExtractedCriterion]) -> list[ExtractedCriterion]:
    """One eligibility row per title across chunks, renumbered E.1, E.2 ... ."""
    scored: dict[str, ExtractedCriterion] = {}
    screened: dict[str, ExtractedCriterion] = {}
    for c in rows:
        if c.stage in ("ELIGIBILITY", "DOCUMENT"):
            c.stage = "ELIGIBILITY"
            kept = screened.setdefault(" ".join(c.title.lower().split()), c)
            kept.proof = kept.proof or c.proof
            kept.rfp_no = kept.rfp_no or c.rfp_no
            kept.source_reference = kept.source_reference or c.source_reference
            kept.classification_unsure = kept.classification_unsure or c.classification_unsure
        else:
            scored.setdefault(c.code, c)
    for n, c in enumerate(screened.values(), start=1):
        c.code, c.parent = f"E.{n}", None
    return [*screened.values(), *scored.values()]


def decimal_or_none(value: str | None) -> Decimal | None:
    try:
        return Decimal(str(value)) if value not in (None, "") else None
    except InvalidOperation:
        return None


# The rule text's general conditions paragraph: this line, then one line per condition,
# - "text" [RFP p. N] (app/rule_text.py reads it back).
GENERAL_HEAD = "GENERAL CONDITIONS (apply to every criterion below)"


def build_block(rows: list[dict], general: list[GeneralCondition] | None = None) -> str:
    """Draft rule text for the prompt: the RFP's general conditions, then every
    criterion with marks the LLM scores (per project, per CV or on the whole bid).

    Group headings are left out: their marks are only the sum of their sub-criteria.
    """
    ways = scoring(rows)
    parts = ["Apply each criterion exactly as the RFP text says. "
             "The plain-words line only explains it."]
    if general:
        parts.append(GENERAL_HEAD + "\n" + "\n".join(
            f"- \"{g.text}\"" + (f" [RFP p. {g.rfp_page}]" if g.rfp_page else "")
            for g in general))
    for c in rows:
        if ways.get(c["code"]) not in ("PROJECT", "CV", "BID"):   # AI-scored rows with marks
            continue
        limit = f", max {c['max_items']} items" if c.get("max_items") else ""
        allowed = c.get("allowed") or "as the RFP text says"
        if c.get("count_bands"):
            bands = describe([CountBand.model_validate(b) for b in c["count_bands"]])
            allowed = f"none per item: marks by the number of qualifying items ({bands})"
        parts.append(f"CRITERION {c['code']}  (max {c['max_marks']} marks{limit})\n"
                     f"RFP text: \"{c['rfp_text']}\"\n"
                     f"In plain words: {c['meaning']}\n"
                     f"Marks one item can earn: {allowed}")
    return "\n\n".join(parts)
