"""One firm's eligibility page: its checks (one per requirement), and the chosen check's
finding, proof quotes in plain language and decision. Presentation only: every result
comes from the check job and every decision from app/eligibility.py.
"""
from app.db import q_eligibility, q_projects
from app.eligibility import firm, number, requirements
from app.evidence_labels import present


def firm_page(cur, check_id: str) -> dict | None:
    chosen = q_eligibility.get_check(cur, check_id)
    project = chosen and q_projects.get_project(cur, chosen["tender_id"])
    if project is None:                        # no such check, or the project was deleted
        return None
    tender_id, submission_id = chosen["tender_id"], chosen["submission_id"]
    sub = next((s for s in q_eligibility.screened_bids(cur, tender_id)
                if s["submission_id"] == submission_id), None)
    if sub is None:
        return None                            # the firm has no bid file
    reqs = requirements(cur, tender_id)
    checks = q_eligibility.current(cur, tender_id, submission_id)
    jobs = q_eligibility.jobs(cur, tender_id)
    row = firm(sub, reqs, checks, jobs.get(submission_id))
    # A link to a replaced check opens the current check of the same requirement.
    current = next((c for c in checks if c["criterion_id"] == chosen["criterion_id"]), None)
    req = next((r for r in reqs if r["criterion_id"] == chosen["criterion_id"]), None)
    return {"project": project, "firm": row, "submission_id": submission_id,
            "titles": {r["code"]: r["title"] for r in reqs},
            "check": _detail(current, req) if current and req else None}


def _detail(check: dict, req: dict) -> dict:
    facts = check["facts"] or {}
    proof = [present(c, facts) for c in check["verification"] or []]
    pages = [p["page"] for p in proof if p["page"]] + list(check["pages"] or [])
    return {"check_id": check["check_id"], "code": req["code"], "number": number(req),
            "stage": req["stage"],
            "title": req["title"],
            "rfp_text": req["rfp_text"],
            "result": check["result"], "finding": check["finding"], "checked": check["checked"],
            "pages": check["pages"] or [], "proof": proof, "first_page": pages[0] if pages else 1,
            "decision": {"decision": check["decision"], "reason": check["decision_reason"],
                         "by": check["decided_by"], "decided": check["decided"]}
            if check["decision"] else None}
