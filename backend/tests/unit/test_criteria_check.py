from decimal import Decimal

from app.criteria import missing_max_marks


def row(code, max_marks, kind="PROJECT", scored_by="LLM", stage="TECHNICAL"):
    return {"code": code, "max_marks": max_marks, "kind": kind, "scored_by": scored_by, "stage": stage}


def test_ai_scored_criterion_without_max_marks_is_reported():
    rows = [row("A.1", Decimal("16")), row("T.1", None), row("T.2", None, kind="CV")]
    message = missing_max_marks(rows)
    assert message.startswith("T.1, T.2: no max marks")


def test_rows_the_ai_does_not_score_are_ignored():
    rows = [row("A.1", Decimal("16")), row("T.3", None, kind=None),
            row("C", None, scored_by="COMMITTEE"), row("E.1", None, stage="ELIGIBILITY")]
    assert missing_max_marks(rows) is None
