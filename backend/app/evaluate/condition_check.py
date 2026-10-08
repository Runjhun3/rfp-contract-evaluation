"""Python recomputes every numeric, date or yes/no test the LLM says it applied.

The LLM names the test in the RFP's own terms (fact, test, threshold); this module
knows no rule, only how to compare numbers, dates and yes/no. The value tested is:
  - duration_months: recomputed from the start_on / end_on facts,
  - experience_years (CV): recomputed from the employment rows (cv_check.py),
  - any other fact: the value the LLM extracted (its quote is verified separately);
    a value stated only as a bound ("more than X") is read as a range (bounds.py).
A yes/no test (e.g. is_completed = true) compares the fact's true/false with it. A test
against words (e.g. a degree) is a judgement of meaning: it is recorded as the AI's
judgement (JUDGED), never compared letter by letter. A test that cannot be recomputed
is recorded as such, never guessed.
"""
import operator
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from dateutil.relativedelta import relativedelta

from app.evaluate.bounds import Range, parse_range, passing_range, settle
from app.evaluate.cv_check import total_months
from app.schemas.llm import Condition, ItemResult
from app.schemas.records import EvidenceCheck

PREFIX = "condition: "
JUDGED = "judged: "       # a test against words: the AI's judgement of meaning
MEANING = "Judged by the AI by meaning: "
TESTS = {">": operator.gt, ">=": operator.ge, "≥": operator.ge, "<": operator.lt,
         "<=": operator.le, "≤": operator.le, "=": operator.eq, "==": operator.eq}
EQUAL = {"=", "=="}
FLAGS = {"true": True, "yes": True, "false": False, "no": False}


def condition_checks(result: ItemResult, as_of: date) -> list[EvidenceCheck]:
    return [_check(result, c, as_of) for c in result.conditions]


def parse_flag(text: str | None) -> bool | None:
    """true/false (or yes/no) as written in a fact or a threshold; else None."""
    return FLAGS.get(str(text or "").strip().lower())


def _check(result: ItemResult, cond: Condition, as_of: date) -> EvidenceCheck:
    name = f"{PREFIX}{cond.fact} {cond.test} {cond.threshold}"
    base = {"label": result.label, "fact": name, "quote_found": True}
    if parse_flag(cond.threshold) is not None:
        return _check_flag(base, cond, _stated(result, cond.fact))
    if not any(ch.isdigit() for ch in cond.threshold):     # words, not a number or date
        return _judged(result, cond)
    value, threshold = _value(result, cond.fact, as_of), parse_value(cond.threshold)
    compare = TESTS.get(cond.test.strip())
    if isinstance(value, tuple) and isinstance(threshold, Decimal):   # a stated bound
        return _check_range(base, cond, value, threshold)
    if None in (value, threshold, compare) or type(value) is not type(threshold):
        return EvidenceCheck(**base, note=f"could not recompute {cond.fact} {cond.test} "
                                          f"{cond.threshold}; the evaluation said "
                                          f"{_word(cond.met)}")
    met = compare(value, threshold)
    note = (f"{cond.fact} = {value}: {cond.test} {cond.threshold} is {_word(met)}"
            + ("" if met == cond.met else f", the evaluation said {_word(cond.met)}"))
    return EvidenceCheck(**base, parsed_value=str(value), value_matches=met == cond.met,
                         note=note)


def _check_flag(base: dict, cond: Condition, stated: str | None) -> EvidenceCheck:
    """A yes/no test: the fact's true/false against the threshold's."""
    value = parse_flag(stated)
    if value is None or cond.test.strip() not in EQUAL:
        return EvidenceCheck(**base, note=f"could not recompute {cond.fact} {cond.test} "
                                          f"{cond.threshold}; the evaluation said "
                                          f"{_word(cond.met)}")
    met = value == parse_flag(cond.threshold)
    note = (f"{cond.fact} = {_word(value)}: {cond.test} {cond.threshold} is {_word(met)}"
            + ("" if met == cond.met else f", the evaluation said {_word(cond.met)}"))
    return EvidenceCheck(**base, parsed_value=_word(value), value_matches=met == cond.met,
                         note=note)


def _judged(result: ItemResult, cond: Condition) -> EvidenceCheck:
    """A test against words: whether the fact means what the RFP asks is the AI's
    judgement (its quote is verified separately), shown as such, never compared."""
    stated = _stated(result, cond.fact)
    said = f' (the document says "{stated}")' if stated else ""
    return EvidenceCheck(label=result.label, fact=f"{JUDGED}{cond.fact} {cond.test} "
                         f"{cond.threshold}", quote_found=True, parsed_value=stated,
                         note=f"{MEANING}{'met' if cond.met else 'not met'}{said}.")


def _stated(result: ItemResult, fact: str) -> str | None:
    found = result.all_facts().get(fact)
    return found.value if found else None


def _check_range(base: dict, cond: Condition, value: Range, threshold: Decimal) -> EvidenceCheck:
    """A value the document states only as a bound ("more than X"): the test is settled
    when the whole range falls on one side of the threshold, otherwise not guessed."""
    shown = f"{'more than' if value[1] else 'at least'} {value[0]}" if value[0] is not None \
        else f"{'less than' if value[3] else 'at most'} {value[2]}"
    passing = passing_range(cond.test, threshold)
    met = settle(value, passing) if passing else None
    if met is None:
        return EvidenceCheck(**base, parsed_value=shown,
                             note=f"{cond.fact} is {shown}: {cond.test} {cond.threshold} cannot "
                                  f"be settled from a bound; the evaluation said {_word(cond.met)}")
    note = (f"{cond.fact} is {shown}: {cond.test} {cond.threshold} is {_word(met)}"
            + ("" if met == cond.met else f", the evaluation said {_word(cond.met)}"))
    return EvidenceCheck(**base, parsed_value=shown, value_matches=met == cond.met, note=note)


def _value(result: ItemResult, fact: str, as_of: date) -> Decimal | date | Range | None:
    facts = result.all_facts()
    if fact == "duration_months":
        start, end = (parse_value(f.value) if (f := facts.get(n)) else None
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
    stated = _stated(result, fact)
    if not stated:
        return None
    return parse_value(stated) or parse_range(stated)


def parse_value(text: str | None) -> Decimal | date | None:
    value = str(text or "").strip().replace(",", "")
    try:
        return date.fromisoformat(value[:10]) if len(value) >= 10 and value[4] == "-" \
            else Decimal(value)
    except (ValueError, InvalidOperation):
        return None


def _word(met: bool) -> str:
    return "true" if met else "false"
