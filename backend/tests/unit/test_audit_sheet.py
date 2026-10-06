from decimal import Decimal as D

from openpyxl import Workbook

from app.export.audit_sheet import audit_sheet

HISTORY = [   # newest first, as q_audit.criteria_history returns it
    {"stamp": "29 Sep 2026 10:30", "who": "chair", "what": "Rule text approved",
     "code": "version 1", "old": None, "new": None},
    {"stamp": "29 Sep 2026 10:20", "who": "chair", "what": "Edited: max_marks", "code": "A.1",
     "old": "10", "new": "12"},
    {"stamp": "29 Sep 2026 10:00", "who": None, "what": "Criteria extracted", "code": None,
     "old": "rfp.pdf · criteria_extraction_v9 · model", "new": None}]
EVENTS = [   # newest first, as q_events.project_history returns it
    {"stamp": "29 Sep 2026 12:00", "who": "chair", "what": "Check eligibility · done",
     "code": "Firm/One", "old": "Bid uploaded", "new": None},
    {"stamp": "29 Sep 2026 11:00", "who": "chair", "what": "Participant added",
     "code": "Firm/One", "old": None, "new": None}]
APPROVALS = [{"version": 1, "stamp": "29 Sep 2026 10:30", "full_name": "chair",
              "approved_criteria": None},
             {"version": 2, "stamp": "30 Sep 2026 09:00", "full_name": "chair",
              "approved_criteria": [{"code": "A.1", "title": "Projects", "stage": "TECHNICAL",
                                     "max_marks": "12", "scored_by": "LLM",
                                     "considered": "considered"}]}]
MARKS = [{"stamp": "30 Sep 2026 15:00", "full_name": "chair", "short_name": "Firm/One",
          "code": "C", "marks": D(6), "reason": ""},
         {"stamp": "30 Sep 2026 16:00", "full_name": "chair", "short_name": "Firm/One",
          "code": "C", "marks": D(8), "reason": "Second panel member's sheet added"}]


def test_the_audit_log_lists_the_setup_oldest_first_then_every_committee_mark():
    book = Workbook()
    audit_sheet(book, {"project": {"name": "Stadium PMU"}, "history": HISTORY,
                       "mark_history": MARKS, "events": EVENTS, "approvals": APPROVALS})
    log = list(book["Audit log"].iter_rows(values_only=True))
    assert log[0] == ("Stadium PMU · audit log",) + (None,) * 5
    assert log[3] == ("When", "Who", "What", "Criterion", "Old value / details", "New value")
    assert log[4][1:3] == ("AI", "Criteria extracted")
    assert log[5][1:] == ("chair", "Edited: max_marks", "A.1", "10", "12")
    assert log[6][2:4] == ("Rule text approved", "version 1")
    rows = [r for r in log if any(v is not None for v in r)]
    events = rows.index(("Participants, firms and jobs",) + (None,) * 5)
    assert rows[events + 2][1:4] == ("chair", "Participant added", "Firm/One")
    assert rows[events + 3][2:5] == ("Check eligibility · done", "Firm/One", "Bid uploaded")
    approved = [r[0] for r in rows]
    assert "Criteria not recorded (approved before they were kept)." in approved
    assert ("A.1", "Projects", "TECHNICAL", "12", "LLM", "considered") in rows
    assert log[-2][1:] == ("chair", "Firm/One", "C", 6, None)
    assert log[-1][4:] == (8, "Second panel member's sheet added")
