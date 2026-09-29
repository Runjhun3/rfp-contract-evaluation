"""API: the criteria read from the RFP, their rule text, and approval."""
from decimal import Decimal, InvalidOperation

from starlette.routing import Route

from app.criteria import group_codes, missing_max_marks, review_view
from app.db import q_projects
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.web.auth import check_csrf
from app.web.common import fail, ok
from app.web.routes_projects import project_head

EDITABLE = ("meaning", "kind", "max_marks", "max_items", "allowed", "scored_by", "group_cap")
BAD_CAP = "Group cap must be a number above 0 and below 10000, or blank."


def _db(request):
    return transaction(request.app.state.settings)


async def criteria_page(request):
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        head = project_head(cur, tender_id, "criteria")
        if head is None:
            return fail("Project not found", 404)
        head.update(review_view(q_projects.criteria(cur, tender_id)),
                    prompt=q_projects.latest_prompt(cur, tender_id))
    return ok(head)


def _cap(value) -> Decimal | None:
    """A group cap from the form: blank means no cap. Raises ValueError if invalid."""
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    try:
        cap = Decimal(text)
        if cap.is_finite() and Decimal(0) < cap < Decimal(10000):
            return cap
    except InvalidOperation:
        pass
    raise ValueError(BAD_CAP)


def _fields(sent: dict, current: dict, is_group: bool) -> dict:
    values = {k: sent.get(k, current[k]) for k in EDITABLE}
    return {"meaning": values["meaning"], "kind": values["kind"] or "",
            "max_marks": values["max_marks"] or None, "max_items": values["max_items"] or None,
            "allowed": [m.strip() for m in str(values["allowed"] or "").split(",") if m.strip()],
            "scored_by": values["scored_by"],
            "group_cap": _cap(values["group_cap"]) if is_group else None}


async def save_criteria(request):
    check_csrf(request)
    tender_id = str(request.path_params["tender_id"])
    body = await request.json()
    sent = {str(c.get("criterion_id")): c for c in body.get("criteria", [])}
    with _db(request) as cur:
        rows = q_projects.criteria(cur, tender_id)
        groups = group_codes(rows)
        try:
            updates = [(r["criterion_id"], _fields(sent.get(r["criterion_id"], {}), r,
                                                   r["code"] in groups)) for r in rows]
        except ValueError as err:
            return fail(str(err))
        for cid, fields in updates:
            q_projects.update_criterion(cur, cid, fields)
        q_projects.save_draft_block(cur, tender_id, str(body.get("block") or ""))
    return ok(None, "Criteria saved")


async def approve_criteria(request):
    check_csrf(request)
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        problem = missing_max_marks(q_projects.criteria(cur, tender_id))
        if problem:
            return fail(problem, 409)
        q_projects.approve_prompt(cur, tender_id, LOCAL_USER_ID)
    return ok(None, "Criteria approved")


routes = [
    Route("/api/v1/projects/{tender_id:uuid}/criteria", criteria_page, methods=["GET"]),
    Route("/api/v1/projects/{tender_id:uuid}/criteria", save_criteria, methods=["POST"]),
    Route("/api/v1/projects/{tender_id:uuid}/criteria/approve", approve_criteria,
          methods=["POST"]),
]
