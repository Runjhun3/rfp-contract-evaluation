"""The rule text the evaluator applies, kept in step with the criteria (decisions.md
D-056). It is drafted from the criteria and the RFP's general conditions
(extract_criteria.build_block), exactly as an extraction drafts it.

On "Save changes", when an edit changes what would be drafted (marks, limits, meaning,
allowed marks, scored per, AI or committee), the rule text is redrafted, unless the
committee has written its own text: typed in this save, or saved earlier and differing
from what the criteria gave. Their text is then kept and a notice says so; "Rebuild
from the criteria" replaces it on request.

The general conditions come from the latest extraction (kept since migration 016).
For a project read before that, they are read back from the saved rule text; that is
safe for an update, which only happens when redrafting the unchanged criteria with
them gives the saved text exactly.
"""
import re

from app.db import q_audit
from app.ingest.extract_criteria import GENERAL_HEAD, GeneralCondition, build_block

UPDATED = "Rule text updated from the criteria."
KEPT = ("Your own edits to the rule text were kept, so it was not updated from the "
        "criteria. Use \"Rebuild from the criteria\" to replace them.")
_CONDITION = re.compile(r'^- "(.*)"(?: \[RFP p\. (\d+)\])?$')


def draft(rows: list[dict], general: list[dict] | None) -> str:
    """The rule text the criteria give (general None: without general conditions)."""
    return build_block(rows, [GeneralCondition.model_validate(g) for g in general or []])


def after_save(cur, tender_id: str, rows: tuple[list[dict], list[dict]], saved: str,
               sent: str) -> tuple[str, str | None]:
    """The rule text to save, and a notice for the committee (None: nothing to say).
    rows: the criteria before and after the save; saved: the rule text before it;
    sent: the rule text as the committee sent it."""
    before, after = rows
    if draft(before, None) == draft(after, None):     # no edit touches the rule text
        return sent, None
    general, _ = general_conditions(cur, tender_id, saved)
    if sent != saved or saved != draft(before, general):
        return sent, KEPT
    return draft(after, general), UPDATED


def rebuilt(cur, tender_id: str, rows: list[dict], saved: str) -> dict:
    """"Rebuild from the criteria": the rule text the saved criteria give, not saved.
    recorded is false when the general conditions were read back from the rule text."""
    general, recorded = general_conditions(cur, tender_id, saved)
    return {"text": draft(rows, general), "recorded": recorded}


def general_conditions(cur, tender_id: str, saved: str) -> tuple[list[dict], bool]:
    """The RFP's general conditions, and whether they come from a recorded extraction
    (else they are read back from the saved rule text)."""
    recorded = q_audit.latest_general(cur, tender_id)
    if recorded is not None:
        return recorded, True
    return read_back(saved), False


def read_back(text: str) -> list[dict]:
    """The general conditions written in a rule text by build_block."""
    for part in text.split("\n\n"):
        lines = part.split("\n")
        if lines[0] == GENERAL_HEAD:
            found = [_CONDITION.match(line) for line in lines[1:]]
            return [{"text": m[1], "rfp_page": int(m[2]) if m[2] else None}
                    for m in found if m]
    return []
