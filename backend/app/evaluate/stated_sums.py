"""Python recomputes every total or average a document states (e.g. a CA certificate's
average turnover over three years) from the figures the AI says it is made of. A
total that does not add up is flagged for the committee, never corrected.

Knows no rule: only sum and average of the named facts, within the amount tolerance.
"""
from decimal import Decimal

from app.config import Settings
from app.evaluate.condition_check import parse_value
from app.schemas.documents import Fact, StatedSum
from app.schemas.records import EvidenceCheck

STATED_SUM = "stated total"
OPS = {"sum": "total", "total": "total", "average": "average", "mean": "average"}


def stated_sums(label: str, sums: list[StatedSum], facts: dict[str, Fact | None],
                settings: Settings) -> list[EvidenceCheck]:
    return [_check(label, s, facts, settings) for s in sums]


def _check(label: str, stated: StatedSum, facts: dict[str, Fact | None],
           settings: Settings) -> EvidenceCheck:
    op = OPS.get(stated.op.strip().lower())
    total, parts = _number(facts.get(stated.result)), [_number(facts.get(p))
                                                        for p in stated.parts]
    shown = facts.get(stated.result)
    base = {"label": label, "fact": STATED_SUM, "quote_found": True,
            "pdf_page_no": shown.page if shown else None, "quote": shown.quote if shown else None}
    if op is None or total is None or not parts or None in parts:
        return EvidenceCheck(**base, note=f"Could not recompute the stated {stated.result}: "
                                          "a figure is missing or not a number.")
    computed = sum(parts, Decimal(0))
    if op == "average":
        computed /= len(parts)
    ok = abs(computed - total) <= abs(total) * settings.amount_tolerance
    what = f"{op} of {', '.join(stated.parts)}"
    note = (f"The stated {what} ({_plain(total)}) matches the figures ({_plain(computed)})."
            if ok else f"The stated {what} is {_plain(total)}, but the figures give "
                       f"{_plain(computed)}.")
    return EvidenceCheck(**base, parsed_value=_plain(computed), value_matches=ok, note=note)


def _number(fact: Fact | None) -> Decimal | None:
    value = parse_value(fact.value) if fact else None
    return value if isinstance(value, Decimal) else None


def _plain(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')).normalize():f}"
