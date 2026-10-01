"""What the committee and the system do on eligibility screening: record a decision on
a check, and queue checks of bids. The rules they follow are in app/eligibility.py."""
from app.db import q_bids, q_eligibility, q_projects
from app.eligibility import requirements

MIN_REASON = 10


def decide(cur, check_id: str, body: dict, user_id: str) -> str | None:
    """Record the committee's decision on a current check. None when saved, else why not."""
    check = q_eligibility.get_check(cur, check_id)
    if check is None:
        return "Check not found"
    latest = [c for c in q_eligibility.current(cur, check["tender_id"], check["submission_id"])
              if c["criterion_id"] == check["criterion_id"]]
    if not latest or latest[0]["check_id"] != check_id:
        return "This check was replaced by a newer one. Reload the page."
    decision = str(body.get("decision") or "").upper()
    if decision not in ("MET", "NOT_MET"):
        return "Choose whether the bid meets the requirement."
    reason = str(body.get("reason") or "").strip()
    why = ("the AI was unsure" if check["result"] == "UNSURE"
           else "you disagree with the AI" if decision != check["result"] else None)
    if why and len(reason) < MIN_REASON:
        return f"Give a reason of at least {MIN_REASON} characters: {why}."
    q_eligibility.record_decision(cur, check_id, decision, reason, user_id)
    return None


def start(cur, tender_id: str) -> str | None:
    """"Check eligibility again": queue every bid. None when queued, else why not."""
    prompt = q_projects.latest_prompt(cur, tender_id)
    if not prompt or prompt["status"] != "APPROVED":
        return "Approve the criteria first."
    if not requirements(cur, tender_id):
        return "This project has no eligibility criteria."
    return None if queue_checks(cur, tender_id) else "Upload at least one bid."


def queue_checks(cur, tender_id: str, submission_ids: list[str] | None = None) -> int:
    """Queue checks for the given bids (default: every bid) once the criteria are
    approved and the tender has eligibility requirements. Returns how many."""
    prompt = q_projects.latest_prompt(cur, tender_id)
    if not prompt or prompt["status"] != "APPROVED" or not requirements(cur, tender_id):
        return 0
    ready = [s["submission_id"] for s in q_bids.ready_submissions(cur, tender_id)]
    chosen = [s for s in ready if submission_ids is None or s in submission_ids]
    for submission_id in chosen:
        q_eligibility.enqueue_check(cur, tender_id, submission_id)
    return len(chosen)
