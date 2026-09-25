"""Load the approved criteria for a tender.

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


def load_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = _FENCE.search(text)
    return match.group(1).strip() if match else text.strip()
