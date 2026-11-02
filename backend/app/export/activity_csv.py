"""An activity log as a CSV file (docs/decisions.md D-060), for auditors who want the
record as a file. UTF-8 with a byte-order mark, so Excel reads the ₹ and · correctly.

A cell that starts with = + - @ (or a tab or carriage return) is prefixed with ' so a
spreadsheet shows it as text and never runs it as a formula: firm, file and criterion
names come from uploads and are not trusted.
"""
import csv
import io

HEADER = ["Date & time", "Who", "Area", "What", "Project", "Details"]
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def safe(value) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(FORMULA_START) else text


def activity_csv(rows: list[dict]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(HEADER)
    for r in rows:
        writer.writerow([safe(r[k]) for k in ("stamp", "who", "area", "what", "project",
                                                 "details")])
    return ("\ufeff" + out.getvalue()).encode("utf-8")


def file_name(project: str | None, today: str) -> str:
    """activity-log-<project>-<YYYY-MM-DD>.csv, with only safe characters in the name."""
    name = "".join(c if c.isalnum() else "-" for c in (project or "all-projects")).strip("-")
    return f"activity-log-{name[:60] or 'project'}-{today}.csv"
