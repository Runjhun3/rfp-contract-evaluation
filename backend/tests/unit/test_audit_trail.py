from decimal import Decimal as D

from app import criteria_edits
from app.results import mark_notes

ROW = {"criterion_id": "a1", "code": "A.1", "title": "Projects", "stage": "TECHNICAL",
       "rfp_text": "Similar assignments", "meaning": "Completed PMU projects", "kind": "PROJECT",
       "max_marks": D(10), "max_items": 5, "allowed": "1, 2", "scored_by": "LLM",
       "considered": True}


def test_only_fields_that_really_changed_are_edits():
    assert criteria_edits.changes(ROW, dict(ROW)) == []
    after = dict(ROW, max_marks=D("12"), allowed="1, 2", considered=False, kind=None)
    assert criteria_edits.changes(ROW, after) == [
        ("kind", "PROJECT", None), ("max_marks", "10", "12"),
        ("considered", "considered", "left out")]
    assert criteria_edits.changes(dict(ROW, meaning=""), dict(ROW, meaning=None)) == []


def test_each_change_is_recorded_with_its_source_and_who(monkeypatch):
    added = []
    monkeypatch.setattr(criteria_edits.q_audit, "add_edit",
                        lambda cur, t, row, field, values, source, user:
                        added.append((row["code"], field, values, source, user)))
    new_row = dict(ROW, criterion_id="b1", code="B.1")              # added: not an edit
    count = criteria_edits.record(None, "t", [ROW], [dict(ROW, meaning="Any PMU project"),
                                                     new_row], "EXTRACTION", None)
    assert count == 1
    assert added == [("A.1", "meaning", ("Completed PMU projects", "Any PMU project"),
                      "EXTRACTION", None)]


def test_a_committee_mark_shows_who_entered_it_and_what_it_replaced():
    entry = {"submission_id": "s1", "criterion_id": "c", "full_name": "chair"}
    history = [dict(entry, marks=D(6), reason="", stamp="30 Sep 2026 15:00"),
               dict(entry, marks=D(8), reason="Second panel sheet", stamp="30 Sep 2026 16:00"),
               dict(entry, submission_id="s2", marks=D(5), reason="", stamp="30 Sep 2026 15:05")]
    assert mark_notes(history) == {
        "s1": {"c": "Changed from 6 to 8 by chair, 30 Sep 2026 16:00: Second panel sheet"},
        "s2": {"c": "Entered by chair, 30 Sep 2026 15:05"}}
