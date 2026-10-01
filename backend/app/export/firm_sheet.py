"""One participant's sheet in the exported workbook.

Its totals and rank; its eligibility checks (the AI's result, the committee's decision
and the finding); each criterion in the RFP's order with its final marks and how they
were settled, and under it every item the participant claimed: the AI's marks, the
committee's latest decision and the final marks. Last, every committee decision on its
eligibility and its marks, oldest first (the full log, repeated decisions included).
"""
import re

from app.criteria import group_codes
from app.export.sheet_data import WORDS, criterion_marks, eligibility_word
from app.export.sheet_style import TITLE, bold_row, page_ranges, pages, style
from app.web.common import format_marks

ELIGIBILITY = ["Code", "Eligibility criterion", "Pages", "", "", "AI",
               "Committee", "", "Finding"]
SCREENING = {"ELIGIBILITY": "eligibility"}
HEADER = ["Code", "Criterion / item", "Pages", "Max marks", "AI marks", "Committee",
          "Counted", "Final marks", "Reason"]
LOG = ["Code", "Item", "Pages", "", "", "Decision", "When (IST) · by", "Final marks", "Reason"]
WIDTHS = [8, 50, 11, 9, 9, 13, 18, 9, 80]
DONE = {"ACCEPT": "accepted", "OVERRIDE": "overridden"}


def firm_sheet(book, firm: dict, data: dict) -> None:
    row = firm["row"]
    sheet = book.create_sheet(_name(row["name"], book.sheetnames))
    same = row["legal_name"] == row["name"]
    sheet.append([row["name"] if same else f"{row['legal_name']} ({row['name']})"])
    results = data["results"]
    committee = None if row["total"] is None else row["total"] - row["docs"]
    sheet.append([f"Rank {row['rank'] or '—'} · document marks {_n(row['docs'])} of "
                  f"{_n(results['docs_max'])} · committee marks {_n(committee)} of "
                  f"{_n(results['committee_max'])} · total {_n(row['total'])} of "
                  f"{_n(results['docs_max'] + results['committee_max'])}"])
    sheet.append([])
    _eligibility(sheet, firm, data["requirements"])
    _marks(sheet, firm, data["criteria"])
    _log(sheet, firm, {r["code"]: r["number"] for r in data["requirements"]})
    style(sheet, header_row=4, widths=WIDTHS)
    sheet["A1"].font = TITLE


def _eligibility(sheet, firm: dict, requirements: list[dict]) -> None:
    if not requirements:
        return
    checks = {c["criterion_id"]: c for c in firm["eligibility"]}
    sheet.append(ELIGIBILITY)
    for req in requirements:
        check = checks.get(req["criterion_id"])
        finding = "\n".join(p for p in (check and check["finding"],
                                        check and check["decision_reason"]
                                        and f"Committee: {check['decision_reason']}") if p)
        ai = WORDS[check["stage"]][check["result"]] if check else ""
        sheet.append([req["number"], req["title"],
                      page_ranges(check["pages"]) if check else "", None, None,
                      ai, eligibility_word(check), None, finding])
    sheet.append([])


def _marks(sheet, firm: dict, criteria: list[dict]) -> None:
    row = firm["row"]
    sheet.append(HEADER)
    bold_row(sheet, sheet.max_row)
    groups = group_codes(criteria)
    for c in criteria:
        sheet.append([c["code"], c["title"], None, c["max_marks"], None,
                      _settled(c, row, groups), None, criterion_marks(c, row, criteria)])
        bold_row(sheet, sheet.max_row)
        for i in (i for i in firm["items"] if i["code"] == c["code"]):
            sheet.append(["", i["title"] or i["label"], pages(i),
                          None, i["marks"] if i["counted"] else None,
                          DONE.get(i["action"], ""), _yes_no(i["final_counted"]),
                          i["final_marks"], _reason(i)])


def _log(sheet, firm: dict, numbers: dict[str, str]) -> None:
    """numbers: each requirement's shown number by code; a row no longer considered
    keeps its code."""
    sheet.append([])
    sheet.append(["Decision log"])
    bold_row(sheet, sheet.max_row)
    sheet.append(LOG)
    bold_row(sheet, sheet.max_row)
    for d in firm["eligibility_log"]:
        sheet.append([numbers.get(d["code"], d["code"]), SCREENING[d["stage"]], "", None, None,
                      WORDS[d["stage"]][d["decision"]],
                      f"{d['decided']} · {d['full_name']}", None, d["reason"]])
    for d in firm["decisions"]:
        sheet.append([d["code"], (d["title"] or d["label"]) if d["label"] else "whole criterion",
                      pages(d) if d["label"] else "", None, None, d["action"].lower(),
                      f"{d['decided']} · {d['full_name']}", d["final_marks"], d["reason"]])


def _settled(criterion: dict, row: dict, groups: set[str]) -> str:
    """How a criterion's marks were settled."""
    if criterion["code"] in groups:
        return ""
    if criterion["criterion_id"] in row["manual"]:
        return "entered"
    cell = row["cells"].get(criterion["code"])
    return "" if cell is None else "approved" if cell["reviewed"] else "not approved"


def _reason(item: dict) -> str:
    """The AI's reason, and the committee's when it gave one."""
    parts = [item["reason"] or ""]
    if item["decision_reason"]:
        parts.append(f"Committee: {item['decision_reason']}")
    return "\n".join(p for p in parts if p)


def _name(short_name: str, taken: list[str]) -> str:
    """A valid, unique sheet name: at most 31 characters, none of []:*?/\\ ."""
    base = re.sub(r"[\[\]:*?/\\]", " ", short_name).strip()[:31] or "Participant"
    name, n = base, 2
    while name.lower() in (t.lower() for t in taken):
        suffix = f" ({n})"
        name, n = base[:31 - len(suffix)] + suffix, n + 1
    return name


def _n(value) -> str:
    return "—" if value is None else format_marks(value)


def _yes_no(value) -> str:
    return "" if value is None else "yes" if value else "no"
