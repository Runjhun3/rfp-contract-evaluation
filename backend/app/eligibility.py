"""Eligibility screening rules: AI findings decide unless the committee overrides.

Every considered eligibility requirement is checked on a bid's latest file. Clear AI
findings decide qualification automatically; only UNSURE findings wait for a committee
decision. Committee decisions are append-only overrides (recorded by app/eligibility_actions.py).
  qualified      when every effective finding is met,
  not qualified  when any effective finding is not met,
  N to decide    while any finding is unsure,
  checking / not checked / check failed  while a check of its latest bid is missing.
While a bid is being checked again, its last results stay on display until replaced;
it is not offered for evaluation until the new check is over.
Only qualified firms are evaluated. A tender without eligibility criteria qualifies
every firm with a bid, as before.
"""
import re

from app.criteria import SCREENED
from app.db import q_eligibility, q_projects

WAITING = {"PENDING", "RUNNING"}


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
                              "number": r["number"]} for r in reqs],
            "firms": firms, "open": sum(f["open"] for f in firms),
            "qualified": sum(1 for f in firms if _can_evaluate(f)),
            "checking": sum(1 for f in firms if f["checking"])}


def _can_evaluate(firm_row: dict) -> bool:
    """Qualified, ticked on the participants page, and not being checked again (its bid
    may have changed). An unticked firm keeps its results but is left out of runs."""
    return (firm_row["status"] == "qualified" and firm_row["included"]
            and not firm_row["checking"])


def requirements(cur, tender_id: str) -> list[dict]:
    """The considered eligibility criteria, in natural code order, each with its number."""
    rows = [c for c in q_projects.criteria(cur, tender_id)
            if c["stage"] in SCREENED and c.get("considered", True)]
    return numbered(sorted(rows, key=lambda c: [int(p) if p.isdigit() else p
                                                for p in re.split(r"(\d+)", c["code"])]))


def numbered(reqs: list[dict]) -> list[dict]:
    """How each requirement is shown: the numbers the RFP prints when it gives every one
    a distinct number, else one running number 1, 2, 3 ... (e.g. a conditions list and a
    documents list each numbered from 1). The code stays the key."""
    printed = [r.get("rfp_no") for r in reqs]
    own = all(printed) and len(set(printed)) == len(printed)
    return [{**r, "number": printed[i] if own else str(i + 1)} for i, r in enumerate(reqs)]


def firm(sub: dict, reqs: list[dict], checks: list[dict], job: dict | None) -> dict:
    """One firm's row: a cell per requirement and its derived status.

    While the bid is being checked again, the last finished checks, their decisions and
    the status they give stay on display ("checking" is set) until the new checks
    replace them. Checks of an older bid file count only then: once the new file's
    check is over (or failed), the status needs checks of the latest file."""
    latest = {c["criterion_id"]: c for c in checks}
    cells = [_cell(r, latest.get(r["criterion_id"])) for r in reqs]
    checking = bool(job and job["status"] in WAITING)
    outdated = any(c["file_id"] != sub["file_id"] for c in latest.values())
    status, label = _status(cells, job, checking, outdated)
    return {"submission_id": sub["submission_id"], "name": sub["short_name"],
            "legal_name": sub["legal_name"], "cells": cells, "status": status,
            "label": label, "checking": checking,
            "included": sub["included"],
            "open": sum(1 for c in cells if c["check_id"] and _effective(c) == "UNSURE"),
            "error": job["error"] if job and status == "failed" else None}


def _cell(req: dict, check: dict | None) -> dict:
    return {"code": req["code"], "number": req["number"], "stage": req["stage"],
            "check_id": check["check_id"] if check else None,
            "result": check["result"] if check else None,
            "decision": check["decision"] if check else None}


def _effective(cell: dict) -> str | None:
    """Committee override when present, otherwise the AI's verified finding."""
    return cell["decision"] or cell["result"]


def _status(cells: list[dict], job: dict | None, checking: bool,
            outdated: bool) -> tuple[str, str]:
    """The firm's status from its considered eligibility checks."""
    if any(not c["check_id"] for c in cells) or (outdated and not checking):
        if checking:
            return "checking", "Checking eligibility"
        failed = job and job["status"] == "FAILED"
        return ("failed", "Check failed") if failed else ("not_checked", "Not checked yet")
    if not cells:
        return "qualified", "No eligibility criteria"
    open_ = sum(1 for c in cells if _effective(c) == "UNSURE")
    if open_:
        return "open", f"{open_} to decide"
    failed = [c["number"] for c in cells if _effective(c) == "NOT_MET"]
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
