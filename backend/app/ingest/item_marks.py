"""The marks one item can earn under a criterion (criterion.allowed_item_marks), from
what the extraction read in the RFP (criteria_extraction_v10):

- item_marks: marks of which exactly one applies (slabs: 3, 4 or 5 by turnover);
- item_mark_parts: separate parts that add up (4 for meeting the criteria + 3 for
  government experience). Python works out every total an item can reach (3, 4 and 7)
  so no sum is left to the AI (coding standards: Python checks every number).

0 is never listed: an item may always earn nothing (evaluate/arithmetic_check.py).
"""
from decimal import Decimal, InvalidOperation
from itertools import combinations

MAX_PARTS = 8          # 255 totals at most; an RFP lists a handful of parts


def _number(value: str) -> Decimal | None:
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    return number if number.is_finite() and number > 0 else None


def possible_item_marks(item_marks: list[str], parts: list[str]) -> list[str]:
    """Every mark one item can earn, smallest first, as plain numbers ("3", "4", "7")."""
    marks = {m for m in (_number(v) for v in item_marks) if m is not None}
    numbers = [p for p in (_number(v) for v in parts) if p is not None][:MAX_PARTS]
    for size in range(1, len(numbers) + 1):
        marks.update(sum(chosen) for chosen in combinations(numbers, size))
    return [format(m.normalize(), "f") for m in sorted(marks)]
