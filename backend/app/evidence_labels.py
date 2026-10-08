"""Plain-language form of one evidence check, for the committee's evidence screen.

Knows only the app's own names (the fact names of the item prompt, the check names
Python writes); values are shown as value_labels.py shows them. It knows no RFP rule
and changes no result.
"""
from app.evaluate.bounds import parse_range, passing_range, settle
from app.evaluate.condition_check import (JUDGED, MEANING, PREFIX, TESTS, parse_flag,
                                          parse_value)
from app.evaluate.date_order import DATE_ORDER
from app.evaluate.document_checks import (CLAIM, COVERAGE, FORENSIC, IDENTIFIER, REFERENCE,
                                          RESOLUTION)
from app.evaluate.proof_check import PROOF
from app.evaluate.rejection_check import REJECTION
from app.evaluate.stated_sums import STATED_SUM
from app.value_labels import show_value

RECHECKED = "re-checked"
NAMES = {"title": "Project title", "client": "Client", "country": "Country",
         "awarded_on": "Award date", "start_on": "Start date", "end_on": "End date",
         "value_inr": "Contract value", "is_completed": "Completed",
         "duration_months": "Duration", "experience_years": "Years of experience",
         "stated_experience": "Experience stated in the CV", "degree": "Degree",
         "work_order_present": "Work order", "completion_or_ca_present":
         "Completion or CA certificate", REJECTION: "Why not eligible",
         RECHECKED: "Re-checked", PROOF: "Reason and proof", "certificate_on":
         "Certificate date", DATE_ORDER: "Order of the dates", STATED_SUM: "Stated total",
         CLAIM: "Firm's claim vs its documents", REFERENCE: "Document referred to",
         RESOLUTION: "Scan resolution", IDENTIFIER: "Identifier on the document",
         FORENSIC: "Document check", COVERAGE: "Document checks made"}
# The document checks (evaluate/document_checks.py): passed, a problem, or a note.
DOCUMENT = (DATE_ORDER, STATED_SUM, CLAIM, REFERENCE, RESOLUTION, IDENTIFIER, FORENSIC,
            COVERAGE)
WORDS = {">": "above", ">=": "at least", "≥": "at least", "<": "below", "<=": "at most",
         "≤": "at most", "=": "equal to", "==": "equal to"}


def present(check: dict, facts: dict) -> dict:
    """{label, detail, quote, page, region, state}; state is problem, note or passed;
    region: the box on the page a forensic finding is about, if any."""
    shown = {"quote": check["quote"], "page": check["pdf_page_no"]}
    if check.get("region"):
        shown["region"] = check["region"]
    if check["fact"].startswith(PREFIX):
        return {**shown, **_test(check)}
    if check["fact"].startswith(JUDGED):
        return {**shown, **_judged(check)}
    if check["fact"] in (REJECTION, RECHECKED, PROOF, *DOCUMENT):
        state = "problem" if check["value_matches"] is False \
            else "passed" if check["fact"] == PROOF or check["value_matches"] else "note"
        note = (check["note"] or "").removeprefix("not eligible: ")
        return {**shown, "label": NAMES[check["fact"]], "state": state, "detail": _sentence(note)}
    return {**shown, "label": fact_name(check["fact"]), **_quote(check, facts)}


def fact_name(name: str) -> str:
    if name.startswith("employment_row_"):
        return f"Employment row {name.rsplit('_', 1)[1]}"
    return NAMES.get(name, name.replace("_", " ").capitalize())


def _test(check: dict) -> dict:
    fact, test, threshold = check["fact"][len(PREFIX):].split(" ", 2)
    if parse_flag(threshold) is not None and check["value_matches"] is not None:
        return _flag(check, fact)
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


def _flag(check: dict, fact: str) -> dict:
    """A yes/no test, recomputed from the fact: e.g. "Completed: Yes"."""
    said = "Yes" if parse_flag(check["parsed_value"]) else "No"
    if check["value_matches"]:
        return {"label": fact_name(fact), "state": "passed",
                "detail": f"{said}, as the RFP's test requires"}
    return {"label": fact_name(fact), "state": "problem",
            "detail": f"The fact says {said.lower()}; the AI's test said otherwise"}


def _judged(check: dict) -> dict:
    """A test against words: the AI's judgement of meaning, shown as such."""
    fact, test, threshold = check["fact"][len(JUDGED):].split(" ", 2)
    met = check["note"].startswith(f"{MEANING}met")
    return {"label": f"{fact_name(fact)} {WORDS.get(test, test)} {threshold}",
            "state": "passed" if met else "note", "detail": check["note"]}


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


def _sentence(text: str | None) -> str:
    text = (text or "").strip()
    return text[:1].upper() + text[1:]
