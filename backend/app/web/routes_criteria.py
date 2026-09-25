"""API: the criteria read from the RFP, their rule text, and approval."""
from decimal import Decimal

from starlette.routing import Route

from app.db import q_projects
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.web.auth import check_csrf
from app.web.common import fail, ok
from app.web.routes_projects import project_head

EDITABLE = ("meaning", "kind", "max_marks", "max_items", "allowed", "scored_by")


def _db(request):
    return transaction(request.app.state.settings)


async def criteria_page(request):
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        head = project_head(cur, tender_id, "criteria")
        if head is None:
            return fail("Project not found", 404)
        head.update(criteria=q_projects.criteria(cur, tender_id),
                    prompt=q_projects.latest_prompt(cur, tender_id))
    head["technical_total"] = sum((c["max_marks"] or Decimal(0) for c in head["criteria"]
                                   if c["stage"] != "ELIGIBILITY"), Decimal(0))
    return ok(head)


def _fields(sent: dict, current: dict) -> dict:
    values = {k: sent.get(k, current[k]) for k in EDITABLE}
    return {"meaning": values["meaning"], "kind": values["kind"] or "",
            "max_marks": values["max_marks"] or None, "max_items": values["max_items"] or None,
            "allowed": [m.strip() for m in str(values["allowed"] or "").split(",") if m.strip()],
            "scored_by": values["scored_by"]}


async def save_criteria(request):
    check_csrf(request)
    tender_id = str(request.path_params["tender_id"])
    body = await request.json()
    sent = {str(c.get("criterion_id")): c for c in body.get("criteria", [])}
    with _db(request) as cur:
        for current in q_projects.criteria(cur, tender_id):
            cid = current["criterion_id"]
            q_projects.update_criterion(cur, cid, _fields(sent.get(cid, {}), current))
        q_projects.save_draft_block(cur, tender_id, str(body.get("block") or ""))
    return ok(None, "Criteria saved")


async def approve_criteria(request):
    check_csrf(request)
    with _db(request) as cur:
        q_projects.approve_prompt(cur, str(request.path_params["tender_id"]), LOCAL_USER_ID)
    return ok(None, "Criteria approved")


routes = [
    Route("/api/v1/projects/{tender_id:uuid}/criteria", criteria_page, methods=["GET"]),
    Route("/api/v1/projects/{tender_id:uuid}/criteria", save_criteria, methods=["POST"]),
    Route("/api/v1/projects/{tender_id:uuid}/criteria/approve", approve_criteria,
          methods=["POST"]),
]
