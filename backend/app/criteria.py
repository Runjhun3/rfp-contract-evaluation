"""Load the approved criteria for a tender, and check they can be scored.

criteria.json : structured rows (code, meaning, max_marks, max_items, allowed marks)
criteria_block: the human-approved rule text that goes into the prompt; in a
                markdown file it is the first ```text fenced block.
"""
import json
import re
from decimal import Decimal
from pathlib import Path

from app.schemas.records import Criterion

_FENCE = re.compile(r"```text\n(.*?)```", re.S)


def load_criteria(path: Path) -> list[Criterion]:
    rows = json.loads(path.read_text(encoding="utf-8"))["criteria"]
    return [Criterion.model_validate(row) for row in rows]


def missing_max_marks(rows: list[dict]) -> str | None:
    """The criteria the AI would score per project/CV but that have no max marks.

    The evaluation cannot cap or check totals without them, so approval and
    starting a run are refused until a person fixes the row. Returns the message
    for the reviewer, or None when every scored criterion is complete.
    """
    groups = group_codes(rows)
    codes = [r["code"] for r in rows if r["stage"] == "TECHNICAL" and r["scored_by"] == "LLM"
             and r["kind"] and r["max_marks"] is None and r["code"] not in groups]
    if not codes:
        return None
    return (f"{', '.join(codes)}: no max marks. If the AI should not score it, set "
            "\"Scored per\" to — (or \"Scored by\" to Committee only), then save.")


def group_codes(rows: list[dict]) -> set[str]:
    """Codes that another row names as its parent: headings such as "A Consultant
    Experience" whose marks are the sum of their sub-criteria. They are never scored
    themselves, at any depth (A → A.1 → A.1.a)."""
    return {r["parent_code"] for r in rows if r.get("parent_code")}


def scored_total(rows: list[dict]) -> Decimal:
    """Max marks of the tender: every non-eligibility criterion except group headings."""
    groups = group_codes(rows)
    return sum((r["max_marks"] or Decimal(0) for r in rows
                if r["stage"] != "ELIGIBILITY" and r["code"] not in groups), Decimal(0))


def group_mismatches(rows: list[dict]) -> list[str]:
    """Groups whose RFP marks differ from the sum of their direct sub-criteria.

    Shown to the reviewer; neither number is corrected.
    """
    problems = []
    for group in rows:
        if group["code"] not in group_codes(rows) or group["max_marks"] is None:
            continue
        parts = sum((r["max_marks"] or Decimal(0) for r in rows
                     if r.get("parent_code") == group["code"]), Decimal(0))
        if parts != group["max_marks"]:
            problems.append(f"{group['code']}: the RFP gives {group['max_marks']} marks, but its "
                            f"sub-criteria add up to {parts}. Check the marks against the RFP.")
    return problems


def review_view(rows: list[dict]) -> dict:
    """The criteria page data: rows flagged as group or scored, the total, and warnings."""
    groups = group_codes(rows)
    return {"criteria": [{**r, "is_group": r["code"] in groups} for r in rows],
            "technical_total": scored_total(rows),
            "group_warnings": group_mismatches(rows)}


def load_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = _FENCE.search(text)
    return match.group(1).strip() if match else text.strip()
