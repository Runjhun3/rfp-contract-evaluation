"""Python checks every number the LLM returned for a criterion. Never corrects.

checked_marks = sum of counted item marks, capped at max_marks.
"""
from decimal import Decimal

from app.schemas.llm import CriterionResult, ItemResult
from app.schemas.records import ArithmeticCheck, Criterion


def check_criterion(criterion: Criterion, result: CriterionResult,
                    items: dict[str, ItemResult]) -> ArithmeticCheck:
    counted = [i for i in result.items if i.counted]
    issues = _item_issues(criterion, result, items)
    if criterion.max_items is not None and len(counted) > criterion.max_items:
        issues.append(f"{len(counted)} items counted, maximum is {criterion.max_items}")
    issues += _best_n_issues(result)
    total = sum((i.marks for i in counted), Decimal(0))
    checked = min(total, criterion.max_marks)
    if result.marks != checked:
        issues.append(f"LLM total {result.marks} but counted items give {checked}")
    return ArithmeticCheck(code=criterion.code, llm_marks=result.marks, checked_marks=checked,
                           ok=not issues, issues=issues)


def _item_issues(criterion: Criterion, result: CriterionResult,
                 items: dict[str, ItemResult]) -> list[str]:
    issues = []
    labels = {i.label for i in result.items}
    for missing in sorted(set(items) - labels):
        issues.append(f"{missing}: item result missing from criterion answer")
    for row in (i for i in result.items if i.counted):
        source = items.get(row.label)
        if source is None:
            issues.append(f"{row.label}: counted but unknown item")
        elif not source.eligible:
            issues.append(f"{row.label}: counted but item was not eligible")
        elif row.marks != source.marks:
            issues.append(f"{row.label}: {row.marks} marks, item said {source.marks}")
        if criterion.allowed_item_marks and row.marks not in criterion.allowed_item_marks:
            issues.append(f"{row.label}: {row.marks} is not an allowed mark "
                          f"{[str(m) for m in criterion.allowed_item_marks]}")
    return issues


def _best_n_issues(result: CriterionResult) -> list[str]:
    counted = [i for i in result.items if i.counted]
    dropped = [i for i in result.items if i.eligible and not i.counted]
    if not counted or not dropped:
        return []
    lowest = min(i.marks for i in counted)
    better = [i.label for i in dropped if i.marks > lowest]
    return [f"not best N: {', '.join(better)} scored higher than a counted item"] if better else []
