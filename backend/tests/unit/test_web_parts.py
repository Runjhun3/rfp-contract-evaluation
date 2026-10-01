from decimal import Decimal

from app.results import _add_eligibility, _ranked, _row
from app.web.common import format_marks, stepper


def test_format_marks():
    assert format_marks(Decimal("12.00")) == "12"
    assert format_marks(Decimal("9.50")) == "9.5"
    assert format_marks(Decimal("10.05")) == "10.05"
    assert format_marks(0) == "0"


def test_stepper_unlocks_steps_by_status():
    project = {"tender_id": "t1", "status": "PROMPT_APPROVED"}
    steps = stepper(project, "participants", None)
    assert [s["key"] for s in steps] == ["rfp", "criteria", "participants", "eligibility",
                                         "evaluate", "results"]
    # Eligibility opens with Participants: bids are screened as they are uploaded.
    assert [s["url"] is not None for s in steps] == [True, True, True, True, False, False]
    assert [s["done"] for s in steps] == [True, True, False, False, False, False]
    assert steps[3]["url"] == "/projects/t1/eligibility"
    # Participants is done once a bid is uploaded, before any evaluation starts.
    with_bids = stepper(project, "eligibility", None, bids_ready=True)
    assert [s["done"] for s in with_bids] == [True, True, True, False, False, False]
    draft = stepper({"tender_id": "t1", "status": "CRITERIA_READY"}, "criteria", None)
    assert draft[3]["url"] is None
    review = stepper({"tender_id": "t1", "status": "REVIEW"}, "results", "r1")
    assert review[5]["url"] == "/projects/t1/results" and review[5]["current"]
    assert review[3]["done"] and review[4]["done"]


def test_results_step_opens_once_any_participant_has_a_finished_evaluation():
    running = {"tender_id": "t1", "status": "EVALUATING"}
    assert stepper(running, "evaluate", "r1")[5]["url"] is None
    early = stepper(running, "evaluate", "r1", results_ready=True)
    assert early[5]["url"] == "/projects/t1/results" and not early[5]["done"]


def _progress(name, stage):
    return {"submission_id": name, "short_name": name, "legal_name": f"{name} Ltd",
            "stage": stage, "included": True}


def test_only_finished_participants_get_marks_and_a_rank():
    cell = {"marks": Decimal("30"), "needs_review": False, "reviewed": False}
    rows = [_row(_progress("A", "DONE"), {"A.1": cell}, {"c": Decimal("25")}),
            _row(_progress("B", "ITEMS"), {}, {"c": None}),
            _row(_progress("C", "DONE"), {"A.1": dict(cell, marks=Decimal("50"))}, {"c": None}),
            _row(_progress("D", "DONE"), {"A.1": dict(cell, marks=Decimal("50"))}, {"c": None}),
            _row(_progress("E", "FAILED"), {}, {"c": Decimal("10")})]
    ranked = [(r["name"], r["rank"], r["total"]) for r in _ranked(rows)]
    assert ranked == [("A", "1", Decimal("55")), ("C", "2=", Decimal("50")),
                      ("D", "2=", Decimal("50")), ("B", None, None), ("E", None, None)]


def test_a_firm_not_evaluated_says_whether_it_failed_eligibility_or_waits_for_it():
    rows = [_row(_progress("A", "DONE"), {}, {"c": Decimal("30")}),
            _row(_progress("B", "NOT_STARTED"), {}, {"c": None}),
            _row(_progress("C", "NOT_STARTED"), {}, {"c": None})]
    _add_eligibility(rows, {
        "A": {"status": "qualified", "label": "Qualified"},
        "B": {"status": "not_qualified", "label": "Not qualified: E.4 not met"},
        "C": {"status": "open", "label": "2 to decide"}})
    assert [(r["eligibility"], r["status"]) for r in rows] == [
        ("qualified", None), ("not_qualified", "Not evaluated: E.4 not met"),
        ("open", "Eligibility pending: 2 to decide")]


def test_a_participant_evaluated_again_shows_no_marks_until_it_finishes():
    cell = {"marks": Decimal("40"), "needs_review": False, "reviewed": False}
    rows = [_row(_progress("EY", "DONE"), {"A.1": cell}, {"c": None}),
            _row(_progress("GT", "ITEMS"), {"A.1": cell}, {"c": Decimal("30")}),     # re-run going
            _row(_progress("PwC", "FAILED"), {}, {"c": None}),
            _row(_progress("New", "NOT_STARTED"), {}, {"c": None})]
    shown = [(r["name"], r["status"], r["total"], r["cells"]) for r in _ranked(rows)]
    assert shown == [("EY", None, Decimal("40"), {"A.1": cell}),
                     ("GT", "Being evaluated", None, {}),
                     ("PwC", "Evaluation failed", None, {}),
                     ("New", "Not evaluated yet", None, {})]
