import io
from decimal import Decimal

from openpyxl import load_workbook

from app.export.annexure_sheet import build_workbook, file_name
from app.results import export_blockers

D = Decimal


CODES = [{"code": "A.1", "max_marks": D(5)}]
COMMITTEE = [{"criterion_id": "c", "code": "C", "title": "Presentation", "max_marks": D(35)}]


def row(name, total, presentation=D(30), cells=None):
    return {"name": name, "total": total, "manual": {"c": presentation},
            "cells": {"A.1": {}} if cells is None else cells}


def test_export_waits_for_evaluations_decisions_and_committee_marks():
    assert export_blockers([], 0, CODES, COMMITTEE) == ["No participant has been evaluated yet."]
    assert export_blockers([row("EY", D(90)), row("GT", None)], 2, CODES, COMMITTEE) == [
        "No finished evaluation yet for GT.", "2 marks are not approved by the committee yet."]
    assert export_blockers([row("EY", D(60), presentation=None)], 0, CODES, COMMITTEE) == [
        "C marks are not entered for EY."]
    assert export_blockers([row("EY", D(60), presentation=None)], 0, CODES, []) == []


def test_a_criterion_with_marks_that_was_never_scored_blocks_the_export():
    assert export_blockers([row("EY", D(60), cells={})], 0, CODES, COMMITTEE) == [
        "A.1 was not scored for EY (evaluated before it could be): evaluate again."]


def test_the_sheet_has_marks_pages_group_totals_and_the_audit_trail():
    criteria = [
        {"criterion_id": "a", "code": "A", "parent_code": None, "stage": "TECHNICAL",
         "title": "Experience", "max_marks": D(20)},
        {"criterion_id": "a1", "code": "A.1", "parent_code": "A", "stage": "TECHNICAL",
         "title": "Projects", "max_marks": D(12)},
        {"criterion_id": "a2", "code": "A.2", "parent_code": "A", "stage": "TECHNICAL",
         "title": "Large projects", "max_marks": D(12)},
        {"criterion_id": "c", "code": "C", "parent_code": None, "stage": "TECHNICAL",
         "title": "Presentation", "max_marks": D(10)}]      # committee-scored, any stage
    cell = {"score_id": "s1", "needs_review": False, "reviewed": True}
    results = {"committee_max": D(10), "docs_max": D(24), "rows": [{
        "submission_id": "b1", "name": "Bidder One", "rank": "1", "manual": {"c": D(8)},
        "cells": {"A.1": dict(cell, marks=D(12)), "A.2": dict(cell, marks=D("10.50"))},
        "docs": D("22.5"), "total": D("30.5")}]}
    items = [{"submission_id": "b1", "participant": "Bidder One", "code": "A.1",
              "title": "Stadium PMU", "label": "A.1 p.10-20", "from_page": 10, "to_page": 20,
              "counted": True, "marks": D(2), "reason": "ok"}]
    decisions = [{"participant": "Bidder One", "code": "A.1", "action": "ACCEPT",
                  "final_marks": D(12), "reason": "Checked against the certificates",
                  "full_name": "Local user", "decided": "29 Sep 2026 12:00"}]
    project = {"name": "Stadium / PMU 2026", "gem_bid_no": "GEM/1", "department": "Dept",
               "due": "07 May 2026"}
    book = load_workbook(io.BytesIO(build_workbook(
        {"project": project, "results": results, "criteria": criteria, "items": items,
         "decisions": decisions})))
    rows = {r[0]: r for r in book["Evaluation"].iter_rows(min_row=6, values_only=True) if r[0]}
    assert rows["A"][3] == D("22.5")
    assert rows["A.1"][3] == "12\nPages: 10–20" and rows["A.2"][3] == "10.5"
    assert rows["C"][3] == 8
    totals = [r for r in book["Evaluation"].iter_rows(values_only=True) if r[1] == "Total"][0]
    assert totals[2:4] == (34, 30.5)
    assert book["Items"].max_row == 2 and book["Decisions"]["C2"].value == "accept"
    assert file_name(project) == "Stadium  PMU 2026 - evaluation sheet.xlsx"
