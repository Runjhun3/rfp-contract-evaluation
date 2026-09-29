"""EVAL_CRITERION: one small LLM call per bidder x criterion, over item results only
(no pages). Applies "maximum N items, keep the best" and totals the marks.

A criterion that gives marks by the number of qualifying items (count bands) needs
no call: every qualifying item counts (up to max items, in the bidder's order) and
the marks are the band the count falls in (count_bands.py).
"""
import json

from app.evaluate.count_bands import band_marks, describe
from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.llm import CriterionItem, CriterionResult, ItemResult
from app.schemas.records import Criterion

SYSTEM = "You total bid evaluation marks by the rules given. Return valid JSON only."


def evaluate_criterion(criterion: Criterion, bidder: str, results: list[ItemResult],
                       llm: LlmClient) -> CriterionResult:
    if not results:
        return CriterionResult(code=criterion.code, items=[], counted_items=0,
                               marks=0, summary="No items submitted for this criterion")
    if criterion.count_bands:
        return count_result(criterion, results)
    user = fill(load("criterion"), code=criterion.code, bidder=bidder,
                max_items=criterion.max_items or "no limit", max_marks=criterion.max_marks,
                item_results=json.dumps(_item_rows(results), indent=1))
    return llm.ask_json(SYSTEM, user, CriterionResult)


def _item_rows(results: list[ItemResult]) -> list[dict]:
    return [{"label": r.label, "order": n, "eligible": r.eligible, "marks": str(r.marks),
             "reason": r.reason} for n, r in enumerate(results, start=1)]


def count_result(criterion: Criterion, results: list[ItemResult]) -> CriterionResult:
    limit = criterion.max_items or len(results)
    rows, counted = [], 0
    for n, r in enumerate(results, start=1):
        counts = r.eligible and counted < limit
        counted += counts
        why = r.reason if counts or not r.eligible else f"Beyond maximum of {limit} items"
        rows.append(CriterionItem(label=r.label, order=n, eligible=r.eligible, counted=counts,
                                  marks=r.marks, reason=why))
    marks = band_marks(criterion.count_bands, counted)
    return CriterionResult(code=criterion.code, items=rows, counted_items=counted, marks=marks,
                           summary=f"{counted} qualifying items counted; marks by number of "
                                   f"items ({describe(criterion.count_bands)}): {marks}")
