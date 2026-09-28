"""Python recomputes every numeric or date test the LLM says it applied.

The LLM names the test in the RFP's own terms (fact, test, threshold); this module
knows no rule, only how to compare numbers and dates. The value tested is:
  - duration_months: recomputed from the start_on / end_on facts,
  - experience_years (CV): recomputed from the employment rows (cv_check.py),
  - any other fact: the value the LLM extracted (its quote is verified separately).
A test that cannot be recomputed is recorded as such, never guessed.
"""
import operator
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from dateutil.relativedelta import relativedelta

from app.evaluate.cv_check import total_months
from app.schemas.llm import Condition, ItemResult
from app.schemas.records import EvidenceCheck

PREFIX = "condition: "
TESTS = {">": operator.gt, ">=": operator.ge, "≥": operator.ge, "<": operator.lt,
         "<=": operator.le, "≤": operator.le, "=": operator.eq, "==": operator.eq}


def condition_checks(result: ItemResult, as_of: date) -> list[EvidenceCheck]:
    return [_check(result, c, as_of) for c in result.conditions]


def findings(checks: list[EvidenceCheck]) -> list[str]:
    """One line per test the LLM got wrong, for the re-check and the record."""
    return [c.note for c in checks if c.fact.startswith(PREFIX) and c.value_matches is False]


def _check(result: ItemResult, cond: Condition, as_of: date) -> EvidenceCheck:
    name = f"{PREFIX}{cond.fact} {cond.test} {cond.threshold}"
    base = {"label": result.label, "fact": name, "quote_found": True}
    value, threshold = _value(result, cond.fact, as_of), _parse(cond.threshold)
    compare = TESTS.get(cond.test.strip())
    if None in (value, threshold, compare) or type(value) is not type(threshold):
        return EvidenceCheck(**base, note=f"could not recompute {cond.fact} {cond.test} "
                                          f"{cond.threshold}; the evaluation said "
                                          f"{_word(cond.met)}")
    met = compare(value, threshold)
    note = (f"{cond.fact} = {value}: {cond.test} {cond.threshold} is {_word(met)}"
            + ("" if met == cond.met else f", the evaluation said {_word(cond.met)}"))
    return EvidenceCheck(**base, parsed_value=str(value), value_matches=met == cond.met,
                         note=note)


def _value(result: ItemResult, fact: str, as_of: date) -> Decimal | date | None:
    facts = result.all_facts()
    if fact == "duration_months":
        start, end = (_parse(f.value) if (f := facts.get(n)) else None
                      for n in ("start_on", "end_on"))
        if isinstance(start, date) and isinstance(end, date) and end >= start:
            span = relativedelta(end + timedelta(days=1), start)   # both days inclusive
            days = (Decimal(span.days) / 30).quantize(Decimal("0.1"))
            return Decimal(span.years * 12 + span.months) + days
        return None
    if fact == "experience_years" and result.cv and result.cv.employment:
        months, unread = total_months(result.cv.employment, as_of)
        if unread == len(result.cv.employment):
            return None                  # no dated rows: cannot recompute, never 0
        return (Decimal(months) / 12).quantize(Decimal("0.1"))
    found = facts.get(fact)
    return _parse(found.value) if found else None


def _parse(text: str | None) -> Decimal | date | None:
    value = str(text or "").strip().replace(",", "")
    try:
        return date.fromisoformat(value[:10]) if len(value) >= 10 and value[4] == "-" \
            else Decimal(value)
    except (ValueError, InvalidOperation):
        return None


def _word(met: bool) -> str:
    return "true" if met else "false"
