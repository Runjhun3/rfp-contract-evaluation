"""Read rupee amounts out of a quote. Returns every amount found, in rupees.

Handles: "INR 9.06 Crore", "Rs. 9,06,00,000/-", "₹ 906 lakh", "9.06 Cr".
"""
import re
from decimal import Decimal, InvalidOperation

UNITS = {
    "crore": Decimal(10) ** 7, "crores": Decimal(10) ** 7, "cr": Decimal(10) ** 7,
    "crs": Decimal(10) ** 7, "lakh": Decimal(10) ** 5, "lakhs": Decimal(10) ** 5,
    "lac": Decimal(10) ** 5, "lacs": Decimal(10) ** 5,
}
_AMOUNT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(crores?|crs?|lakhs?|lacs?)?\b", re.IGNORECASE)


def parse_amounts(quote: str) -> list[Decimal]:
    found = []
    for number, unit in _AMOUNT.findall(quote):
        try:
            value = Decimal(number.replace(",", ""))
        except InvalidOperation:
            continue
        found.append(value * UNITS.get(unit.lower(), Decimal(1)) if unit else value)
    return found


def amount_matches(fact_value: str, quote: str, tolerance: Decimal) -> tuple[bool, str]:
    target = Decimal(str(fact_value).replace(",", ""))
    amounts = parse_amounts(quote)
    for amount in amounts:
        if target and abs(amount - target) <= abs(target) * tolerance:
            return True, str(amount)
    return False, ", ".join(str(a) for a in amounts)
