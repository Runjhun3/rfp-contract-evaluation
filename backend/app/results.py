"""The results matrix of a project: one row per participant, ranked, across runs.

Each participant shows its most recent evaluation. While that evaluation is still
running (e.g. the participant is being evaluated again) its row has no marks or
rank; when it finishes, its new marks replace the old ones. Participants evaluated
in earlier runs keep their results, so a new run never hides them.

Columns come from the approved criteria, not from what happened to be scored: every
criterion with marks is shown (app/criteria.py `scoring`). AI-scored ones show their
final marks; committee-scored ones (e.g. a presentation) take the committee's marks.
"""
from decimal import Decimal

from app import eligibility
from app.criteria import scoring
from app.db import q_projects, q_results

STATUS = {"DONE": None, "FAILED": "Evaluation failed", "NOT_STARTED": "Not evaluated yet"}
EVALUATING = "Being evaluated"


def project_results(cur, tender_id: str) -> dict:
    tree = q_projects.criteria(cur, tender_id)
    ways = scoring(tree)
    ai = [c for c in tree if ways.get(c["code"]) in ("PROJECT", "CV", "BID")]
    committee = [{"criterion_id": c["criterion_id"], "code": c["code"], "title": c["title"],
                  "max_marks": c["max_marks"]} for c in tree if ways.get(c["code"]) == "COMMITTEE"]
    latest = q_results.latest_attempts(cur, tender_id)
    cells = _cells(cur, [p for p in latest if p["stage"] == "DONE"])
    entered = q_results.manual_marks(cur, [c["criterion_id"] for c in committee])
    def manual(submission_id: str) -> dict:
        return {c["criterion_id"]: entered.get(c["criterion_id"], {}).get(submission_id)
                for c in committee}

    rows = _ranked([_row(p, cells.get(p["submission_id"], {}), manual(p["submission_id"]))
                    for p in latest])
    screening = eligibility.overview(cur, tender_id)
    _add_eligibility(rows, {f["submission_id"]: f for f in screening["firms"]})
    # Every mark needs the committee's approval, flagged or not.
    open_reviews = sum(1 for r in rows for c in r["cells"].values() if not c["reviewed"])
    pending = sum(1 for r in rows if r["total"] is None)
    codes = [{"code": c["code"], "max_marks": c["max_marks"]} for c in ai]
    return {"codes": codes, "committee": committee, "rows": rows, "open_reviews": open_reviews,
            "evaluating": sum(1 for r in rows if r["status"] == EVALUATING),
            "pending": pending, "ready": pending < len(rows),
            "docs_max": sum((c["max_marks"] for c in ai), Decimal(0)),
            "committee_max": sum((c["max_marks"] for c in committee), Decimal(0)),
            "export_blockers": export_blockers(rows, open_reviews, codes, committee,
                                               screening["open"])}


def _cells(cur, done: list[dict]) -> dict[str, dict]:
    """Final marks of each finished participant, by submission then criterion code."""
    cells: dict[str, dict] = {}
    for s in q_results.scores(cur, [p["run_id"] for p in done],
                              [p["submission_id"] for p in done]):
        cells.setdefault(s["submission_id"], {})[s["code"]] = s
    return cells


def _add_eligibility(rows: list[dict], firms: dict[str, dict]) -> None:
    """Each row's eligibility status; a firm that was not evaluated because it is not
    qualified, or not decided yet, says so in place of marks."""
    for row in rows:
        firm = firms.get(row["submission_id"])
        row["eligibility"] = firm["status"] if firm else None
        if row["total"] is not None or firm is None or firm["status"] == "qualified":
            continue
        row["status"] = (firm["label"].replace("Not qualified", "Not evaluated", 1)
                         if firm["status"] == "not_qualified"
                         else f"Eligibility pending: {firm['label'].lower()}")


def export_blockers(rows: list[dict], open_reviews: int, codes: list[dict],
                    committee: list[dict], open_checks: int) -> list[str]:
    """Why the committee sheet cannot be exported yet; empty when it can. A firm found
    not qualified is complete without an evaluation."""
    if not rows:
        return ["No participant has been evaluated yet."]
    blockers = []
    if open_checks:
        blockers.append(f"{open_checks} eligibility check{'s are' if open_checks > 1 else ' is'}"
                        " not decided by the committee yet.")
    waiting = [r["name"] for r in rows
               if r["total"] is None and r.get("eligibility") != "not_qualified"]
    if waiting:
        blockers.append(f"No finished evaluation yet for {', '.join(waiting)}.")
    finished = [r for r in rows if r["total"] is not None]
    for c in codes:
        missed = [r["name"] for r in finished if c["code"] not in r["cells"]]
        if missed:
            blockers.append(f"{c['code']} was not scored for {', '.join(missed)} "
                            "(evaluated before it could be): evaluate again.")
    if open_reviews:
        blockers.append(f"{open_reviews} mark{'s are' if open_reviews > 1 else ' is'} not "
                        "approved by the committee yet.")
    for c in committee:
        missing = [r["name"] for r in finished if r["manual"].get(c["criterion_id"]) is None]
        if missing:
            blockers.append(f"{c['code']} marks are not entered for {', '.join(missing)}.")
    return blockers


def _row(attempt: dict, cells: dict, manual: dict) -> dict:
    done = attempt["stage"] == "DONE"
    docs = sum((c["marks"] for c in cells.values()), Decimal(0)) if done else None
    extra = sum((m for m in manual.values() if m is not None), Decimal(0))
    return {"submission_id": attempt["submission_id"], "name": attempt["short_name"],
            "legal_name": attempt["legal_name"],
            "included": attempt["included"],
            "stage": attempt["stage"], "status": STATUS.get(attempt["stage"], EVALUATING),
            "cells": cells if done else {}, "docs": docs, "manual": manual, "rank": None,
            "total": docs + extra if done else None}


def _ranked(rows: list[dict]) -> list[dict]:
    """Finished participants by total (ties share a rank, e.g. "2="), then the rest."""
    done = sorted((r for r in rows if r["total"] is not None),
                  key=lambda r: r["total"], reverse=True)
    for row in done:
        tied = [r for r in done if r["total"] == row["total"]]
        row["rank"] = f"{done.index(tied[0]) + 1}{'=' if len(tied) > 1 else ''}"
    return done + [r for r in rows if r["total"] is None]
