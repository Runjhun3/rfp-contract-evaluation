"""The committee's evaluation sheet as an Excel workbook (openpyxl).

Evaluation: one row per criterion in the RFP's order (group headings with the sum
of their sub-criteria; committee-scored criteria such as a presentation with the
committee's marks), one column per participant in rank order;
each cell holds the final marks and the pages of the items counted, like the
committee's own Annexure III sheet. Items and Decisions sheets carry the audit
trail. Built only from the project's data; no RFP is named in code.
"""
import io
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from app.config import TIMEZONE
from app.criteria import group_codes
from app.web.common import format_marks

BOLD = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def build_workbook(data: dict) -> bytes:
    book = Workbook()
    _evaluation(book.active, data)
    _table(book.create_sheet("Items"),
           ["Participant", "Code", "Item", "Pages", "Counted", "Marks", "Reason"],
           [[i["participant"], i["code"], i["title"] or i["label"],
             _pages(i), _yes_no(i["counted"]), i["marks"] if i["counted"] else None,
             i["reason"]] for i in data["items"]], [16, 8, 50, 12, 9, 8, 80])
    _table(book.create_sheet("Decisions"),
           ["Participant", "Code", "Decision", "Final marks", "Reason", "By", "When (IST)"],
           [[d["participant"], d["code"], d["action"].lower(), d["final_marks"], d["reason"],
             d["full_name"], d["decided"]] for d in data["decisions"]],
           [16, 8, 11, 11, 70, 16, 18])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def file_name(project: dict) -> str:
    safe = re.sub(r"[^A-Za-z0-9 ._-]+", "", project["name"]).strip() or "project"
    return f"{safe} - evaluation sheet.xlsx"


def _evaluation(sheet, data: dict) -> None:
    project, results = data["project"], data["results"]
    rows = results["rows"]
    sheet.title = "Evaluation"
    now = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d %b %Y %H:%M")
    sheet.append([project["name"]])
    sheet.append([" · ".join(v for v in (project["gem_bid_no"], project["department"],
                                          f"bids closed {project['due']}") if v)])
    sheet.append([f"Exported {now} IST. Marks are the committee's final marks."])
    sheet.append([])
    sheet.append(["Code", "Criterion", "Max marks", *[r["name"] for r in rows]])
    groups = group_codes(data["criteria"])
    for c in data["criteria"]:
        sheet.append([c["code"], c["title"], c["max_marks"],
                      *[_cell(c, r, data["criteria"], groups, data["items"]) for r in rows]])
    sheet.append(["", "Document marks total", results["docs_max"], *[r["docs"] for r in rows]])
    sheet.append(["", "Total", results["docs_max"] + results["committee_max"],
                  *[r["total"] for r in rows]])
    sheet.append(["", "Rank", None, *[r["rank"] for r in rows]])
    _style(sheet, header_row=5, widths=[8, 60, 10, *[24] * len(rows)])
    for row in sheet.iter_rows(min_row=sheet.max_row - 2):
        for cell in row:
            cell.font = BOLD
    sheet["A1"].font = Font(bold=True, size=14)


def _cell(criterion: dict, row: dict, criteria: list[dict], groups: set[str],
          items: list[dict]):
    code = criterion["code"]
    if code in groups:
        return _group_total(code, criteria, row)
    if criterion["criterion_id"] in row["manual"]:       # entered by the committee
        return row["manual"][criterion["criterion_id"]]
    score = row["cells"].get(code)
    if score is None:
        return None
    counted = [_pages(i) for i in items if i["submission_id"] == row["submission_id"]
               and i["code"] == code and i["counted"]]
    return "\n".join([format_marks(score["marks"])]
                     + ([f"Pages: {', '.join(counted)}"] if counted else []))


def _group_total(code: str, criteria: list[dict], row: dict):
    """A group heading's marks: the sum of its sub-criteria's final marks (or committee
    marks), at any depth; empty when none of them has marks."""
    parts = []
    for child in (c for c in criteria if c.get("parent_code") == code):
        nested = any(c.get("parent_code") == child["code"] for c in criteria)
        value = (_group_total(child["code"], criteria, row) if nested
                 else row["manual"].get(child["criterion_id"])
                 if child["criterion_id"] in row["manual"]
                 else (row["cells"].get(child["code"]) or {}).get("marks"))
        if value is not None:
            parts.append(value)
    return sum(parts) if parts else None


def _table(sheet, header: list[str], rows: list[list], widths: list[int]) -> None:
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    _style(sheet, header_row=1, widths=widths)


def _style(sheet, header_row: int, widths: list[int]) -> None:
    for n, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(n)].width = width
    for row in sheet.iter_rows(min_row=header_row):
        for cell in row:
            cell.alignment = WRAP
    for cell in sheet[header_row]:
        cell.font = BOLD
    sheet.freeze_panes = sheet.cell(row=header_row + 1, column=1)


def _pages(item: dict) -> str:
    start, end = item["from_page"], item["to_page"]
    return str(start) if start == end else f"{start}–{end}"


def _yes_no(value) -> str:
    return "" if value is None else "yes" if value else "no"
