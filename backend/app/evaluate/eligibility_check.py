"""CHECK_ELIGIBILITY: one LLM call per bid x eligibility requirement, over only the pages
the labeller tagged as its proof, then Python's verification of the answer.

The answer is a recommendation (met / not met / unsure); the committee decides every
check (app/eligibility.py). Python checks, and never corrects:
  - every quote is on its page, and that page is one the AI was given,
  - every amount (fact named *_inr) or date (*_on) is what its quote states,
  - every numeric or date test gives the same result when recomputed.
A requirement with no tagged page gets no call: it is unsure, for the committee to look.
"""
from datetime import date

from app.config import Settings
from app.evaluate.condition_check import condition_checks
from app.evaluate.evidence_check import check_fact
from app.evaluate.item_eval import render_pages
from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.llm import EligibilityResult, ItemResult
from app.schemas.records import EvidenceCheck, Item, Page, Requirement

RESULTS = ("MET", "NOT_MET", "UNSURE")
NO_PAGES = ("No page of the bid was found as proof of this requirement. Check the bid "
            "for {proof} and decide.")


def check_requirement(req: Requirement, bidder: str, pages: dict[int, Page],
                      system: str, llm: LlmClient) -> tuple[EligibilityResult, list[int]]:
    """The AI's answer and the pages it was given."""
    tagged = [n for n, p in sorted(pages.items()) if req.code in p.eligibility]
    if not tagged:
        proof = req.proof or "the proof the RFP asks for"
        return EligibilityResult(code=req.code, result="UNSURE",
                                 finding=NO_PAGES.format(proof=proof)), []
    user = fill(load("eligibility"), bidder=bidder, code=req.code, title=req.title,
                rfp_text=req.rfp_text or req.meaning,
                proof=req.proof or "(the RFP names no document)",
                pages=render_pages(_item(req.code, tagged), pages))
    result = llm.ask_json(system, user, EligibilityResult)
    result.code = req.code
    result.result = result.result.strip().upper() if result.result.strip().upper() in RESULTS \
        else "UNSURE"
    return result, tagged


def verify(result: EligibilityResult, tagged: list[int], pages: dict[int, Page],
           settings: Settings, as_of: date) -> list[EvidenceCheck]:
    """Python's checks of the answer: quotes, amounts and dates, recomputed tests."""
    if not tagged:
        return []
    item = _item(result.code, tagged)
    checks = [check_fact(item, name, fact, pages, settings, _kind(name))
              for name, fact in result.facts.items()]
    # condition_check recomputes tests over an item result; the facts and tests are the
    # same shape, so the answer is read as one (marks and confidence play no part).
    as_item = ItemResult(label=result.code, code=result.code, facts=result.facts,
                         conditions=result.conditions, eligible=result.result == "MET",
                         marks=0, reason=result.finding, confidence=1.0)
    return checks + condition_checks(as_item, as_of)


def _kind(name: str) -> str | None:
    return "amount" if name.endswith("_inr") else "date" if name.endswith("_on") else None


def _item(code: str, tagged: list[int]) -> Item:
    """The pages given for a requirement, as an item, so the item checks apply."""
    return Item(label=code, title=f"Proof of {code}", kind="BID", criterion_code=code,
                map_confidence=1.0, from_page=tagged[0], to_page=tagged[-1], pages=tagged)
