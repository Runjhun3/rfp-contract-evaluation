"""Eligibility screening rules: where each firm stands, the committee's decisions, and
starting the checks (docs/decisions.md, D-045, D-046).

Screening checks two kinds of requirement on a bid's latest file: eligibility criteria
(pass/fail) and documents every bid must include. Every AI check is a recommendation
until the committee decides it. Only eligibility criteria decide a firm's status:
  qualified      when every eligibility check is decided as met,
  not qualified  when any is decided as not met (and none is still open),
  N to decide    while any eligibility check is undecided,
  checking / not checked / check failed  while a check of its latest bid is missing.
While a bid is being checked again, its last results stay on display until replaced;
it is not offered for evaluation until the new check is over.
A document decided as not submitted is flagged on the firm ("missing"), never
disqualifying; undecided documents still count as open, so the sheet waits for them.
Only qualified firms are evaluated. A tender without eligibility criteria qualifies
every firm with a bid, as before.
"""
import re

from app.criteria import SCREENED
from app.db import q_bids, q_eligibility, q_projects

WAITING = {"PENDING", "RUNNING"}
MIN_REASON = 10


def overview(cur, tender_id: str) -> dict:
    """The screening grid: requirements, every firm with a bid, and the counts."""
    reqs = requirements(cur, tender_id)
    checks = q_eligibility.current(cur, tender_id)
    jobs = q_eligibility.jobs(cur, tender_id)
    firms = [firm(s, reqs, [c for c in checks if c["submission_id"] == s["submission_id"]],
                  jobs.get(s["submission_id"]))
             for s in q_eligibility.screened_bids(cur, tender_id)]
    return {"requirements": [{**{k: r[k] for k in ("criterion_id", "code", "stage", "title",
                                                   "meaning")},
                              "number": number(r)} for r in reqs],
            "firms": firms, "open": sum(f["open"] for f in firms),
            "qualified": sum(1 for f in firms if _can_evaluate(f)),
            "checking": sum(1 for f in firms if f["checking"])}


def _can_evaluate(firm_row: dict) -> bool:
    """Qualified, ticked on the participants page, and not being checked again (its bid
    may have changed). An unticked firm keeps its results but is left out of runs."""
    return (firm_row["status"] == "qualified" and firm_row["included"]
            and not firm_row["checking"])


def requirements(cur, tender_id: str) -> list[dict]:
    """What screening checks: eligibility criteria, then required documents, each in
    number order (E.2 before E.10)."""
    rows = [c for c in q_projects.criteria(cur, tender_id) if c["stage"] in SCREENED]
    return sorted(rows, key=lambda c: [SCREENED.index(c["stage"])]
                  + [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", c["code"])])


def number(req: dict) -> str:
    """How a requirement is shown: the number the RFP prints for it, else its own code
    (the code stays the key: RFP numbers clash across lists, e.g. "A" of a documents
    list and criterion A)."""
    return req.get("rfp_no") or req["code"]


def firm(sub: dict, reqs: list[dict], checks: list[dict], job: dict | None) -> dict:
    """One firm's row: a cell per requirement (its latest finished check), its status,
    and the documents it was found not to have submitted.

    While the bid is being checked again, the last finished checks, their decisions and
    the status they give stay on display ("checking" is set) until the new checks
    replace them. Checks of an older bid file count only then: once the new file's
    check is over (or failed), the status needs checks of the latest file."""
    latest = {c["criterion_id"]: c for c in checks}
    cells = [_cell(r, latest.get(r["criterion_id"])) for r in reqs]
    checking = bool(job and job["status"] in WAITING)
    outdated = any(c["file_id"] != sub["file_id"] for c in latest.values())
    missing = [c["number"] for c in cells
               if c["stage"] == "DOCUMENT" and c["decision"] == "NOT_MET"]
    status, label = _status(cells, job, checking, outdated)
    return {"submission_id": sub["submission_id"], "name": sub["short_name"],
            "legal_name": sub["legal_name"], "cells": cells, "status": status,
            "label": label, "missing": missing, "checking": checking,
            "included": sub["included"],
            "open": sum(1 for c in cells if c["check_id"] and not c["decision"]),
            "error": job["error"] if job and status == "failed" else None}


def _cell(req: dict, check: dict | None) -> dict:
    return {"code": req["code"], "number": number(req), "stage": req["stage"],
            "check_id": check["check_id"] if check else None,
            "result": check["result"] if check else None,
            "decision": check["decision"] if check else None}


def _status(cells: list[dict], job: dict | None, checking: bool,
            outdated: bool) -> tuple[str, str]:
    """The firm's status, from its eligibility checks only (documents never decide it)."""
    if any(not c["check_id"] for c in cells) or (outdated and not checking):
        if checking:
            return "checking", "Checking eligibility"
        failed = job and job["status"] == "FAILED"
        return ("failed", "Check failed") if failed else ("not_checked", "Not checked yet")
    criteria = [c for c in cells if c["stage"] == "ELIGIBILITY"]
    if not criteria:
        return "qualified", "No eligibility criteria"
    open_ = sum(1 for c in criteria if not c["decision"])
    if open_:
        return "open", f"{open_} to decide"
    failed = [c["number"] for c in criteria if c["decision"] == "NOT_MET"]
    if failed:
        word = "criterion" if len(failed) == 1 else "criteria"
        return "not_qualified", f"Not qualified: {word} {', '.join(failed)} not met"
    return "qualified", "Qualified"


def qualified(cur, tender_id: str) -> list[dict]:
    """The firms with a bid the committee has found eligible and that are not being
    checked again, as their rows."""
    return [f for f in overview(cur, tender_id)["firms"] if _can_evaluate(f)]


def left_out(cur, tender_id: str, in_run: set[str]) -> list[dict]:
    """Firms with a bid that a run did not evaluate, and why (not qualified, pending)."""
    return [{"name": f["name"],
             "label": ("Unticked on participants" if not f["included"]
                       else "Checking eligibility again" if f["checking"] else f["label"])}
            for f in overview(cur, tender_id)["firms"]
            if f["submission_id"] not in in_run and not _can_evaluate(f)]


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
