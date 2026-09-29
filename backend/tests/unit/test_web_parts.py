from decimal import Decimal

from app.results import _ranked, _row
from app.web.common import format_marks, stepper


def test_format_marks():
    assert format_marks(Decimal("12.00")) == "12"
    assert format_marks(Decimal("9.50")) == "9.5"
    assert format_marks(Decimal("10.05")) == "10.05"
    assert format_marks(0) == "0"


def test_stepper_unlocks_steps_by_status():
    project = {"tender_id": "t1", "status": "PROMPT_APPROVED"}
    steps = stepper(project, "participants", None)
    assert [s["url"] is not None for s in steps] == [True, True, True, False, False]
    assert [s["done"] for s in steps] == [True, True, False, False, False]
    review = stepper({"tender_id": "t1", "status": "REVIEW"}, "results", "r1")
    assert review[4]["url"] == "/projects/t1/results" and review[4]["current"]


def test_results_step_opens_once_any_participant_has_a_finished_evaluation():
    running = {"tender_id": "t1", "status": "EVALUATING"}
    assert stepper(running, "evaluate", "r1")[4]["url"] is None
    early = stepper(running, "evaluate", "r1", results_ready=True)
    assert early[4]["url"] == "/projects/t1/results" and not early[4]["done"]


def _progress(name, stage):
    return {"submission_id": name, "short_name": name, "stage": stage, "included": True}


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
