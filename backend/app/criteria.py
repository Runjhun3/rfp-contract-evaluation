"""Load the approved criteria for a tender, and check they can be scored.

criteria.json : structured rows (code, meaning, max_marks, max_items, allowed marks)
criteria_block: the human-approved rule text that goes into the prompt; in a
                markdown file it is the first ```text fenced block.
"""
import json
import re
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
    codes = [r["code"] for r in rows if r["stage"] == "TECHNICAL" and r["scored_by"] == "LLM"
             and r["kind"] and r["max_marks"] is None]
    if not codes:
        return None
    return (f"{', '.join(codes)}: no max marks. If the AI should not score it, set "
            "\"Scored per\" to — (or \"Scored by\" to Committee only), then save.")


def load_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = _FENCE.search(text)
    return match.group(1).strip() if match else text.strip()
