"""Plain-language form of one evidence check, for the committee's evidence screen.

Knows only the app's own names (the fact names of the item prompt, the check names
Python writes) and how to show a value from its suffix (_inr money, _on a date,
_months, _years). It knows no RFP rule and changes no result.
"""
from datetime import date
from decimal import Decimal

from app.evaluate.bounds import parse_range, passing_range, settle
from app.evaluate.condition_check import PREFIX, TESTS, parse_value
from app.evaluate.proof_check import PROOF
from app.evaluate.rejection_check import REJECTION

RECHECKED = "re-checked"
NAMES = {"title": "Project title", "client": "Client", "country": "Country",
         "awarded_on": "Award date", "start_on": "Start date", "end_on": "End date",
         "value_inr": "Contract value", "is_completed": "Completed",
         "duration_months": "Duration", "experience_years": "Years of experience",
         "stated_experience": "Experience stated in the CV", "degree": "Degree",
         "work_order_present": "Work order", "completion_or_ca_present":
         "Completion or CA certificate", REJECTION: "Why not eligible",
         RECHECKED: "Re-checked", PROOF: "Reason and proof"}
WORDS = {">": "above", ">=": "at least", "≥": "at least", "<": "below", "<=": "at most",
         "≤": "at most", "=": "equal to", "==": "equal to"}


def present(check: dict, facts: dict) -> dict:
    """{label, detail, quote, page, state}; state is problem, note or passed."""
    shown = {"quote": check["quote"], "page": check["pdf_page_no"]}
    if check["fact"].startswith(PREFIX):
        return {**shown, **_test(check)}
    if check["fact"] in (REJECTION, RECHECKED, PROOF):
        state = "problem" if check["value_matches"] is False \
            else "passed" if check["fact"] == PROOF else "note"
        note = (check["note"] or "").removeprefix("not eligible: ")
        return {**shown, "label": NAMES[check["fact"]], "state": state, "detail": _sentence(note)}
    return {**shown, "label": fact_name(check["fact"]), **_quote(check, facts)}


def fact_name(name: str) -> str:
    if name.startswith("employment_row_"):
        return f"Employment row {name.rsplit('_', 1)[1]}"
    return NAMES.get(name, name.replace("_", " ").capitalize())


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


def _test(check: dict) -> dict:
    fact, test, threshold = check["fact"][len(PREFIX):].split(" ", 2)
    label = f"{fact_name(fact)} {WORDS.get(test, test)} {show_value(fact, threshold)}"
    value = parse_value(check["parsed_value"]) or parse_range(check["parsed_value"])
    limit = parse_value(threshold)
    if check["value_matches"] is None or value is None or limit is None or test not in TESTS:
        return {"label": label, "state": "note",
                "detail": "Could not be recomputed from the facts; please check it."}
    if isinstance(value, tuple):                # a stated bound, settled as a range
        met = settle(value, passing_range(test, limit))
    else:
        met = TESTS[test](value, limit)
    answer = f"{'Yes' if met else 'No'} ({show_value(fact, check['parsed_value'])})"
    if check["value_matches"]:
        return {"label": label, "state": "passed", "detail": answer}
    return {"label": label, "state": "problem",
            "detail": f"Python: {answer}; the AI said {'no' if met else 'yes'}"}


def _quote(check: dict, facts: dict) -> dict:
    page = check["pdf_page_no"]
    used = (facts.get(check["fact"]) or {}).get("value")
    if check["fact"] == "experience_years":             # re-added from employment rows
        state = {False: "problem", None: "note"}.get(check["value_matches"], "passed")
        return {"state": state, "detail": _sentence(check["note"])}
    if not check["quote_found"]:
        where = f" on page {page}" if page else ""
        detail = _sentence(check["note"]) if check["note"] else f"Not found{where}"
        return {"state": "problem", "detail": detail}
    if check["value_matches"] is False:
        if (check["parsed_value"] or "").startswith("unreadable"):
            return {"state": "problem",
                    "detail": f"The value used is not a plain number or date: {used}"}
        return {"state": "problem", "detail": "The quote does not state the value used"
                                              + (f" ({show_value(check['fact'], used)})"
                                                 if used else "")}
    return {"state": "passed", "detail": f"Found on page {page}" if page else "Found"}


def _rupees(amount: Decimal) -> str:
    for size, word in ((Decimal(10) ** 7, "crore"), (Decimal(10) ** 5, "lakh")):
        if amount >= size:
            return f"₹{_plain(amount / size)} {word}"
    return f"₹{_plain(amount)}"


def _plain(number: Decimal) -> str:
    return format(number.quantize(Decimal("0.01")).normalize(), "f")


def _sentence(text: str | None) -> str:
    text = (text or "").strip()
    return text[:1].upper() + text[1:]
