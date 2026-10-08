"""The workbook's last sheet: the project's audit trail, oldest first.
- Criteria setup: each extraction of the RFP, each edited criterion field (by the
  committee, or by a re-extraction: the AI), each rule text save and approval.
- Participants, firms and jobs: firms ticked or unticked, added, renamed or deleted,
  and every job with why and by whom it was started.
- Approved criteria: the criteria as they stood at each approval.
- Committee marks: every mark entered, with who, when and why it changed.
The per-firm sheets keep the decision logs on marks and eligibility (what the committee
found in a check's documents is the reason for its decision on that check, D-062)."""
from app.export.sheet_style import BOLD, TITLE, bold_row, style

AUDIT = "Audit log"
SETUP = ["When", "Who", "What", "Criterion", "Old value / details", "New value"]
EVENTS = ["When", "Who", "What", "Firm", "Details", "New value"]
APPROVED = ["Code", "Title", "Stage", "Max marks", "Scored by", "Counts"]
MARKS = ["When", "Who", "Firm", "Criterion", "Marks", "Reason"]


def audit_sheet(book, data: dict) -> None:
    sheet = book.create_sheet(AUDIT)
    sheet.append([f"{data['project']['name']} · audit log"])
    sheet.append(["Times are IST. Who = the signed-in account; AI = an extraction of the RFP."])
    sheet.append([])
    sheet.append(SETUP)
    for h in reversed(data["history"]):                       # oldest first
        sheet.append([h["stamp"], h["who"] or "AI", h["what"], h["code"], h["old"], h["new"]])
    style(sheet, header_row=4, widths=[18, 18, 26, 14, 60, 60])
    _section(sheet, "Participants, firms and jobs", EVENTS,
             [[e["stamp"], e["who"] or "system", e["what"], e["code"], e["old"], e["new"]]
              for e in reversed(data["events"])])
    _approved(sheet, data["approvals"])
    _section(sheet, "Committee marks", MARKS,
             [[m["stamp"], m["full_name"], m["short_name"], m["code"], m["marks"],
               m["reason"] or None] for m in data["mark_history"]])
    sheet["A1"].font = TITLE


def _approved(sheet, approvals: list[dict]) -> None:
    """Each approval's criteria; approvals from before they were kept say so."""
    sheet.append([])
    sheet.append(["Approved criteria"])
    bold_row(sheet, sheet.max_row)
    for a in approvals:
        sheet.append([f"Version {a['version']} approved {a['stamp']} by {a['full_name']}"])
        sheet.cell(row=sheet.max_row, column=1).font = BOLD
        if a["approved_criteria"] is None:
            sheet.append(["Criteria not recorded (approved before they were kept)."])
            continue
        sheet.append(APPROVED)
        for c in a["approved_criteria"]:
            sheet.append([c["code"], c["title"], c["stage"], c["max_marks"], c["scored_by"],
                          c["considered"]])


def _section(sheet, title: str, header: list[str], rows: list[list]) -> None:
    sheet.append([])
    sheet.append([title])
    bold_row(sheet, sheet.max_row)
    sheet.append(header)
    bold_row(sheet, sheet.max_row)
    for row in rows:
        sheet.append(row)
