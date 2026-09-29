"""Group caps: a group heading's total is min(sum of its sub-criteria, cap).

Applied by Python to the final marks (after committee decisions), when results
are shown or exported. The uncapped sum is kept beside the capped total so the
committee can see what was trimmed. A trimmed group is marked CAP_APPLIED: that
is information (the RFP working as intended), never a review reason.
"""
from decimal import Decimal

CAP_APPLIED = "CAP_APPLIED"


def apply_caps(criteria: list[dict], marks: dict[str, Decimal]) -> tuple[dict, Decimal]:
    """criteria: rows with code, parent_code, group_cap. marks: one bidder's final
    marks by criterion code. Returns ({group code: {sum, total, flags}}, document
    total). A group none of whose parts has marks is left out."""
    codes = {c["code"] for c in criteria}
    caps = {c["code"]: c.get("group_cap") for c in criteria}
    groups: dict[str, dict] = {}

    def total(code: str) -> Decimal | None:
        kids = [c["code"] for c in criteria if c.get("parent_code") == code]
        if not kids:
            return marks.get(code)
        parts = [t for t in map(total, kids) if t is not None]
        if not parts:
            return None
        raw = sum(parts, Decimal(0))
        capped = min(raw, caps[code]) if caps[code] is not None else raw
        groups[code] = {"sum": raw, "total": capped,
                        "flags": [CAP_APPLIED] if capped < raw else []}
        return capped

    top = [c["code"] for c in criteria if c.get("parent_code") not in codes]
    docs = sum((t for t in map(total, top) if t is not None), Decimal(0))
    return groups, docs
