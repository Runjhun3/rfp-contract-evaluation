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
# Eligibility rows are screened before evaluation and are never scored.
SCREENED = ("ELIGIBILITY",)


def load_criteria(path: Path) -> list[Criterion]:
    rows = json.loads(path.read_text(encoding="utf-8"))["criteria"]
    return [Criterion.model_validate(row) for row in rows]


def scoring(rows: list[dict]) -> dict[str, str]:
    """How each criterion with marks is scored, by code. A criterion with marks entered
    is always scored and shown; only group headings (whose marks are their sub-rows')
    and eligibility rows are left out.
      PROJECT / CV : the AI scores it per project or per CV,
      BID          : the AI scores it once on the whole bid (e.g. turnover),
      COMMITTEE    : the committee enters its marks (e.g. a presentation)."""
    groups = group_codes(rows)
    ways = {}
    for r in rows:
        if r["stage"] in SCREENED or r["code"] in groups or r["max_marks"] is None:
            continue
        ways[r["code"]] = "COMMITTEE" if r["scored_by"] == "COMMITTEE" else r["kind"] or "BID"
    return ways


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


def _children(rows: list[dict], code: str) -> list[dict]:
    return [r for r in rows if r.get("parent_code") == code]


def _best(rows: list[dict], row: dict) -> Decimal:
    """The most a bidder can score on a row: its marks, or for a group the sum of its
    parts."""
    kids = _children(rows, row["code"])
    if not kids:
        return row["max_marks"] or Decimal(0)
    return sum((_best(rows, k) for k in kids), Decimal(0))


def scored_total(rows: list[dict]) -> Decimal:
    """Max marks of the tender: every scored criterion except group headings."""
    codes = {r["code"] for r in rows}
    return sum((_best(rows, r) for r in rows
                if r["stage"] not in SCREENED and r.get("parent_code") not in codes), Decimal(0))


def group_view(rows: list[dict], group: dict) -> dict:
    """A group heading's computed total, beside the marks the RFP states for it.

    parts_total is the plain sum of the sub-rows; rfp_matches compares it with the
    RFP's figure (None when the RFP gives none). Shown to the reviewer; neither number
    is corrected.
    """
    parts = [r["max_marks"] or Decimal(0) for r in _children(rows, group["code"])]
    total = sum(parts, Decimal(0))
    return {"parts": parts, "parts_total": total,
            "rfp_matches": None if group["max_marks"] is None else total == group["max_marks"]}


def items_warning(row: dict) -> str | None:
    """Max items × the highest mark per item should give the criterion's marks."""
    allowed = [Decimal(m) for m in str(row.get("allowed") or "").split(",") if m.strip()]
    if (not allowed or row.get("max_items") is None or row["max_marks"] is None
            or row.get("count_bands")):             # marks by number of items: no per-item mark
        return None
    best = row["max_items"] * max(allowed)
    if best == row["max_marks"]:
        return None
    return (f"{row['max_items']} items × {max(allowed)} = {best}, "
            f"but Marks is {row['max_marks']}")


def review_view(rows: list[dict]) -> dict:
    """The criteria page data: group headings with their computed totals, scored rows
    with their item check, and the scored total."""
    groups = group_codes(rows)
    view = [{**r, "is_group": True, **group_view(rows, r)} if r["code"] in groups
            else {**r, "is_group": False, "items_warning": items_warning(r)} for r in rows]
    return {"criteria": view, "technical_total": scored_total(rows)}


def load_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = _FENCE.search(text)
    return match.group(1).strip() if match else text.strip()
