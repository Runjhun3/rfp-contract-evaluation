from decimal import Decimal

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
    assert review[4]["url"] == "/runs/r1/results" and review[4]["current"]
