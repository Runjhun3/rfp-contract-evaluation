"""EVAL_CRITERION: one small LLM call per bidder x criterion, over item results only
(no pages). Applies "maximum N items, keep the best" and totals the marks.
"""
import json

from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.llm import CriterionResult, ItemResult
from app.schemas.records import Criterion

SYSTEM = "You total bid evaluation marks by the rules given. Return valid JSON only."


def evaluate_criterion(criterion: Criterion, bidder: str, results: list[ItemResult],
                       llm: LlmClient) -> CriterionResult:
    if not results:
        return CriterionResult(code=criterion.code, items=[], counted_items=0,
                               marks=0, summary="No items submitted for this criterion")
    user = fill(load("criterion"), code=criterion.code, bidder=bidder,
                max_items=criterion.max_items or "no limit", max_marks=criterion.max_marks,
                item_results=json.dumps(_item_rows(results), indent=1))
    return llm.ask_json(SYSTEM, user, CriterionResult)


def _item_rows(results: list[ItemResult]) -> list[dict]:
    return [{"label": r.label, "order": n, "eligible": r.eligible, "marks": str(r.marks),
             "reason": r.reason} for n, r in enumerate(results, start=1)]
