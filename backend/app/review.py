"""The committee's decisions and marks.

Decisions: one per item (project, CV or whole-bid evidence), or one on the whole
criterion when it has no items. Accepting keeps the AI's marks for the item (its
marks if counted, else 0) and needs no reason; overriding sets the item's marks and
needs a reason of at least 10 characters. The criterion's final marks follow from the
item decisions in the database view final_score (migration 006).

Committee marks: the marks the committee enters itself for committee-scored criteria
(e.g. a presentation).
"""
from decimal import Decimal, InvalidOperation

from app.criteria import scoring
from app.db import q_projects, q_results

MIN_REASON = 10


def ai_marks(item: dict) -> Decimal:
    """What accepting an item keeps: the AI's marks if it was counted, else 0."""
    return item["marks"] if item["counted"] and item["marks"] is not None else Decimal(0)


def item_limit(score: dict) -> Decimal | None:
    """The most one item can earn under the criterion: the highest of its listed
    per-item marks; 1 under a criterion scored by the number of qualifying items
    (1 = the item counts); None when the criterion lists no per-item marks."""
    if score.get("count_bands"):
        return Decimal(1)
    listed = [Decimal(m) for m in score.get("allowed_item_marks") or []]
    return max(listed) if listed else None


def override_problem(marks: Decimal, score: dict, per_item: bool) -> str | None:
    """An item override is any mark from 0 up to the most one item can earn (0 or 1
    under a criterion scored by the number of qualifying items); without per-item
    marks, or for the whole criterion, 0 up to the criterion's max."""
    if not marks.is_finite() or marks < 0:
        return "Enter the overriding marks as a number of 0 or more."
    limit = item_limit(score) if per_item else None
    if per_item and score.get("count_bands") and marks not in (0, 1):
        return "This criterion counts qualifying items: enter 1 if the item counts, 0 if not."
    if limit is not None and marks > limit:
        return f"Overriding marks for one item can be at most {format(limit.normalize(), 'f')}."
    if limit is None and score["max_marks"] is not None and marks > score["max_marks"]:
        return f"Overriding marks must be between 0 and {score['max_marks']}."
    return None


def decide(cur, score_id: str, body: dict, user_id: str) -> str | None:
    """Record one decision; returns an error message for the reviewer, or None."""
    score = q_results.score_detail(cur, score_id)
    if score is None:
        return "Score not found"
    items = q_results.items(cur, score["run_id"], score["submission_id"], score["criterion_id"])
    item_id = body.get("item_id") or None
    item = next((i for i in items if i["item_id"] == item_id), None)
    if item_id and item is None:
        return "That item does not belong to this criterion."
    if item is None and items:
        return "Decide each project or CV of this criterion."
    action = "OVERRIDE" if body.get("action") == "OVERRIDE" else "ACCEPT"
    reason = str(body.get("reason") or "").strip()
    if action == "ACCEPT":
        marks = ai_marks(item) if item else score["checked_marks"]
    else:
        try:
            marks = Decimal(str(body.get("marks")).strip())
        except InvalidOperation:
            return "Enter the overriding marks as a number."
        problem = override_problem(marks, score, item is not None)
        if problem:
            return problem
        if len(reason) < MIN_REASON:
            return f"Give a reason of at least {MIN_REASON} characters to override."
    q_results.record_decision(cur, score_id, item_id, action, marks, reason, user_id)
    return None


def save_committee_marks(cur, tender_id: str, sent: dict, user_id: str) -> str | None:
    """Marks the committee enters for committee-scored criteria (e.g. a presentation):
    {criterion_id: {submission_id: marks}}. A blank entry is skipped; any other bad
    value rejects the whole save. Returns an error message, or None."""
    tree = q_projects.criteria(cur, tender_id)
    ways = scoring(tree)
    committee = {c["criterion_id"]: c for c in tree if ways.get(c["code"]) == "COMMITTEE"}
    known = {a["submission_id"] for a in q_results.latest_attempts(cur, tender_id)}
    parsed = []
    for criterion_id, by_bidder in (sent or {}).items():
        criterion = committee.get(str(criterion_id))
        if criterion is None:
            return "Those marks are not for a committee-scored criterion of this project."
        for submission_id, value in (by_bidder or {}).items():
            text = str(value if value is not None else "").strip()
            if not text or str(submission_id) not in known:
                continue
            try:
                marks = Decimal(text)
            except InvalidOperation:
                marks = None
            if marks is None or not marks.is_finite() or not 0 <= marks <= criterion["max_marks"]:
                return (f"{criterion['code']} marks must be numbers from 0 to "
                        f"{criterion['max_marks']}.")
            parsed.append((str(submission_id), criterion["criterion_id"], marks))
    for submission_id, criterion_id, marks in parsed:
        q_results.save_manual_mark(cur, submission_id, criterion_id, marks, user_id)
    return None
