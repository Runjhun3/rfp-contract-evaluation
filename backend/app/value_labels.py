"""How a value reads on the committee's screens, from its fact's suffix: _inr money
(₹ crore / lakh), _on a date, _months and _years a count; a stated bound ("more than
X") reads as such. Knows no RFP rule and changes no result."""
from datetime import date
from decimal import Decimal

from app.evaluate.bounds import parse_range
from app.evaluate.condition_check import parse_value


def show_value(fact: str, value) -> str:
    bound = parse_range(str(value))
    if bound:                                   # "more than 300000000000" etc.
        number = bound[0] if bound[0] is not None else bound[2]
        if bound[0] is not None:
            word = "more than" if bound[1] else "at least"
        else:
            word = "less than" if bound[3] else "at most"
        return f"{word} {show_value(fact, str(number))}"
    parsed = parse_value(str(value))
    if isinstance(parsed, date):
        return f"{parsed.day} {parsed:%b %Y}"
    if isinstance(parsed, Decimal) and fact.endswith("_inr"):
        return _rupees(parsed)
    for suffix, unit in (("_months", "months"), ("_years", "years")):
        if isinstance(parsed, Decimal) and fact.endswith(suffix):
            return f"{_plain(parsed)} {unit}"
    return str(value)


def _rupees(amount: Decimal) -> str:
    for size, word in ((Decimal(10) ** 7, "crore"), (Decimal(10) ** 5, "lakh")):
        if amount >= size:
            return f"₹{_plain(amount / size)} {word}"
    return f"₹{_plain(amount)}"


def _plain(number: Decimal) -> str:
    return format(number.quantize(Decimal("0.01")).normalize(), "f")
