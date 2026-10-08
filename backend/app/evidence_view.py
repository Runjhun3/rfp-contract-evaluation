"""The committee's evidence screen for one criterion score: the items grouped by
outcome (items needing attention marked), and the chosen item's verdict, checks in
plain language and decision. Presentation only: every score and flag comes from the
evaluation run; nothing here changes one.
"""
from decimal import Decimal

from app.db import q_projects, q_results
from app.evaluate.condition_check import PREFIX
from app.evaluate.document_checks import REASONS
from app.evaluate.proof_check import PROOF
from app.evaluate.rejection_check import REJECTION
from app.evidence_labels import RECHECKED, present
from app.review import ai_marks, item_limit

# Item-level review reasons that need the committee (docs/pipeline.md): an item with
# one of them gets the attention dot. Context-only reasons (scanned pages, low-confidence
# mapping) do not.
DECIDE = {"CONDITION_MISMATCH", "UNSUPPORTED_REJECTION", "NO_PROOF", "RECHECKED",
          "EVIDENCE_UNVERIFIED", "LOW_CONFIDENCE", "COPY_MISMATCH", "SUSPICIOUS_TEXT",
          "DATE_ORDER", "STATED_SUM", "CLAIM_DIFFERS", "REFERENCE_MISSING",
          "DOCUMENT_ID", "DOCUMENT_FLAG"}
GROUPS = (("counted", "Counted"), ("not_counted", "Not counted"),
          ("not_scored", "Not scored"))


def evidence_view(cur, score_id: str, chosen: str | None, threshold: Decimal) -> dict | None:
    score = q_results.score_detail(cur, score_id)
    project = score and q_projects.get_project(cur, score["tender_id"])
    if project is None:                               # no such score, or project deleted
        return None
    items = q_results.items(cur, score["run_id"], score["submission_id"], score["criterion_id"])
    checks = q_results.checks(cur, [i["item_id"] for i in items])
    flags = {i["item_id"]: _flags(i, [c for c in checks if c["item_id"] == i["item_id"]],
                                  threshold) for i in items}
    item = next((i for i in items if i["item_id"] == chosen), items[0] if items else None)
    mine = [c for c in checks if item and c["item_id"] == item["item_id"]]
    counted = [i for i in items if i["counted"]]
    return {"score": score,
            "progress": {"items": len(items), "counted": len(counted),
                         "decided": sum(1 for i in counted if i["decision"])},
            "groups": _groups(items, flags),
            "item": _verdict(item, score, threshold) if item else None,
            "checks": [present(c, item["facts"] or {}) for c in mine] if item else [],
            "project": project}


def _flags(item: dict, checks: list[dict], threshold: Decimal) -> set[str]:
    """The review reasons this one item contributes (same rules as evaluate/flags.py)."""
    if item["eligible"] is None:
        return set()
    found = set()
    if item["confidence"] < threshold:
        found.add("LOW_CONFIDENCE")
    if item["map_confidence"] < threshold:
        found.add("MAPPING_UNSURE")
    if item["suspicious_text"]:
        found.add("SUSPICIOUS_TEXT")
    if item["copy_mismatches"] and item["counted"]:
        found.add("COPY_MISMATCH")
    for c in checks:
        if c["fact"] in REASONS:
            if c["value_matches"] is False:
                found.add(REASONS[c["fact"]])
        elif c["fact"] == RECHECKED:
            found.add("RECHECKED")
        elif c["value_matches"] is False and c["fact"].startswith(PREFIX):
            found.add("CONDITION_MISMATCH")
        elif c["value_matches"] is False and c["fact"] == REJECTION:
            found.add("UNSUPPORTED_REJECTION")
        elif c["value_matches"] is False and c["fact"] == PROOF:
            found.add("NO_PROOF")
        elif c["fact"] == PROOF:
            continue
        elif item["counted"] and (not c["quote_found"] or c["value_matches"] is False):
            found.add("EVIDENCE_UNVERIFIED")
    return found


def _groups(items: list[dict], flags: dict[str, set[str]]) -> list[dict]:
    rows: dict[str, list[dict]] = {key: [] for key, _ in GROUPS}
    for i in items:
        group = _status(i)
        final = i["final_marks"] if i["final_counted"] or i["decision"] else None
        rows[group].append({"item_id": i["item_id"], "title": _title(i), "pages": _pages(i),
                            "marks": final, "decision": i["decision"],
                            # the highlight dot: flagged and not yet decided by the committee
                            "attention": bool(flags[i["item_id"]] & DECIDE) and not i["decision"]})
    return [{"key": key, "label": label, "items": rows[key]} for key, label in GROUPS
            if rows[key]]


def _status(item: dict) -> str:
    """Where an item stands in the FINAL marks (final_item view): counted when it is
    among the best items with marks, whether the AI or the committee put it there."""
    if item["final_counted"]:
        return "counted"
    return "not_scored" if item["eligible"] is None and not item["decision"] else "not_counted"


def _verdict(item: dict, score: dict, threshold: Decimal) -> dict:
    status = _status(item)
    reason = item["count_reason"] if not item["counted"] and item["count_reason"] \
        else item["reason"]
    return {"item_id": item["item_id"], "title": _title(item), "pages": _pages(item),
            "from_page": item["from_page"], "status": status,
            "marks": item["final_marks"] if status == "counted" else item["marks"],
            "confidence": round(item["confidence"] * 100) if item["confidence"] else None,
            "reason": reason or "Not evaluated: another copy of this item was scored.",
            "judgement_call": bool(item["eligible"] and item["confidence"] < threshold),
            "ai_marks": ai_marks(item), "counted_by_ai": bool(item["counted"]),
            "count_based": bool(score.get("count_bands")),
            "item_limit": item_limit(score) if item_limit(score) is not None
            else score["max_marks"],                   # the most an override can give
            "decision": {"action": item["decision"], "final_marks": item["decided_marks"],
                         "reason": item["decision_reason"]} if item["decision"] else None}


def _title(item: dict) -> str:
    return item["title"] or item["label"]


def _pages(item: dict) -> str:
    start, end = item["from_page"], item["to_page"]
    return f"p. {start}" if start == end else f"p. {start}–{end}"
