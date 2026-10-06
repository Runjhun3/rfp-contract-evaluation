"""The criteria edit trail: compare a project's criteria before and after a change and
record each field that changed (docs/decisions.md D-053). Both sides come from the same
query (q_projects.criteria), so values compare as the committee sees them."""
from app.db import q_audit

TRACKED = ("title", "stage", "rfp_text", "meaning", "kind", "max_marks", "max_items",
           "allowed", "scored_by", "considered")


def shown(field: str, value) -> str | None:
    """A field's value as the trail records it; None when blank."""
    if value is None or value == "":
        return None
    if field == "considered":
        return "considered" if value else "left out"
    return str(value)


def snapshot(rows: list[dict]) -> list[dict]:
    """The criteria as approved: each row's code and tracked fields, as the trail
    shows them (kept with the approved rule text)."""
    return [{"code": r["code"], **{f: shown(f, r.get(f)) for f in TRACKED}} for r in rows]


def changes(before: dict, after: dict) -> list[tuple[str, str | None, str | None]]:
    """(field, old, new) for every tracked field whose shown value differs."""
    pairs = [(f, shown(f, before.get(f)), shown(f, after.get(f))) for f in TRACKED]
    return [(f, old, new) for f, old, new in pairs if old != new]


def record(cur, tender_id: str, before: list[dict], after: list[dict], source: str,
           user_id: str | None) -> int:
    """Record what changed between two readings of the criteria; returns how many
    fields. Rows added or dropped are not edits: an extraction's snapshot holds them."""
    old = {c["criterion_id"]: c for c in before}
    count = 0
    for row in after:
        if row["criterion_id"] not in old:
            continue
        for field, was, now in changes(old[row["criterion_id"]], row):
            q_audit.add_edit(cur, tender_id, row, field, (was, now), source, user_id)
            count += 1
    return count
