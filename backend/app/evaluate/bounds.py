"""Values stated as a bound rather than a figure: "more than 3000", "> 3000",
"at least 5", "up to 10", "below 2". A document often certifies only that a figure
is above or below something (e.g. "turnover of more than INR 3,000 crore").

A bound is read as a range, and a test on it is settled only when the whole range
falls on one side of the threshold ("more than 3000" is certainly above 750; whether
it is above 5000 is unknown). Plain language and symbols only; no RFP rule.
"""
import re
from decimal import Decimal, InvalidOperation

# (words or symbol, which side, open end): "more than 5" -> (5, inf) is ("lo", True)
_BOUNDS = [(r">=|≥|at least|not less than|minimum of|min\.?", "lo", False),
           (r">|more than|greater than|above|over|exceeding|in excess of", "lo", True),
           (r"<=|≤|at most|not more than|up to|maximum of|max\.?", "hi", False),
           (r"<|less than|below|under", "hi", True)]
_PATTERN = re.compile(
    r"^\s*(" + "|".join(p for p, _, _ in _BOUNDS) + r")(?![a-z])\s*(.+)$", re.IGNORECASE)

# A range: (low, low is open, high, high is open); None = unbounded on that side.
Range = tuple[Decimal | None, bool, Decimal | None, bool]


def split_bound(text: str) -> tuple[str | None, str]:
    """("lo"/"hi" or None, the number text without the bound words)."""
    match = _PATTERN.match(str(text or ""))
    if not match:
        return None, str(text or "")
    word = match.group(1).lower()
    side = next(s for p, s, _ in _BOUNDS if re.fullmatch(p, word, re.IGNORECASE))
    return side, match.group(2)


def parse_range(text: str) -> Range | None:
    """The range a bounded value states, or None when it is not a numeric bound."""
    match = _PATTERN.match(str(text or ""))
    if not match:
        return None
    word = match.group(1).lower()
    side, is_open = next((s, o) for p, s, o in _BOUNDS
                         if re.fullmatch(p, word, re.IGNORECASE))
    try:
        number = Decimal(match.group(2).strip().replace(",", ""))
    except InvalidOperation:
        return None
    return (number, is_open, None, False) if side == "lo" else (None, False, number, is_open)


def passing_range(test: str, threshold: Decimal) -> Range | None:
    """The values that pass a test such as "> 50" or "<= 10"."""
    return {">": (threshold, True, None, False), ">=": (threshold, False, None, False),
            "≥": (threshold, False, None, False), "<": (None, False, threshold, True),
            "<=": (None, False, threshold, False), "≤": (None, False, threshold, False),
            "=": (threshold, False, threshold, False),
            "==": (threshold, False, threshold, False)}.get(test.strip())


def settle(value: Range, passing: Range) -> bool | None:
    """True if every value in the range passes, False if none does, None if unknown."""
    if _inside(value, passing):
        return True
    if _apart(value, passing):
        return False
    return None


def _inside(a: Range, b: Range) -> bool:
    lo = b[0] is None or (a[0] is not None and (
        a[0] > b[0] or (a[0] == b[0] and (a[1] or not b[1]))))
    hi = b[2] is None or (a[2] is not None and (
        a[2] < b[2] or (a[2] == b[2] and (a[3] or not b[3]))))
    return lo and hi


def _apart(a: Range, b: Range) -> bool:
    def below(x: Range, y: Range) -> bool:          # all of x lies under all of y
        return x[2] is not None and y[0] is not None and (
            x[2] < y[0] or (x[2] == y[0] and (x[3] or y[1])))
    return below(a, b) or below(b, a)
