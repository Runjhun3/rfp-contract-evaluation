"""API: the criteria read from the RFP, their rule text, and approval."""
from starlette.routing import Route

from app import criteria_edits, eligibility_actions, rule_text
from app.criteria import missing_max_marks, review_view
from app.db import q_projects, q_prompts
from app.db.connection import transaction
from app.web.auth import check_csrf, current_user
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
        head.update(review_view(q_projects.criteria(cur, tender_id)),
                    prompt=q_projects.latest_prompt(cur, tender_id))
    return ok(head)


def _fields(sent: dict, current: dict) -> dict:
    values = {k: sent.get(k, current[k]) for k in EDITABLE}
    return {"meaning": values["meaning"], "kind": values["kind"] or "",
            "max_marks": values["max_marks"] or None, "max_items": values["max_items"] or None,
            "allowed": [m.strip() for m in str(values["allowed"] or "").split(",") if m.strip()],
            "scored_by": values["scored_by"],
            "considered": bool(sent.get("considered", current.get("considered", True)))}


async def save_criteria(request):
    check_csrf(request)
    tender_id = str(request.path_params["tender_id"])
    body = await request.json()
    sent = {str(c.get("criterion_id")): c for c in body.get("criteria", [])}
    user_id = current_user(request)
    with _db(request) as cur:
        before = q_projects.criteria(cur, tender_id)
        for current in before:
            cid = current["criterion_id"]
            q_projects.update_criterion(cur, cid, _fields(sent.get(cid, {}), current))
        after = q_projects.criteria(cur, tender_id)
        criteria_edits.record(cur, tender_id, before, after, "COMMITTEE", user_id)
        saved = (q_projects.latest_prompt(cur, tender_id) or {}).get("criteria_block", "")
        block, notice = rule_text.after_save(cur, tender_id, (before, after), saved,
                                             str(body.get("block") or ""))
        q_prompts.save_draft_block(cur, tender_id, block, user_id)
    return ok({"notice": notice}, "Criteria saved")


async def rebuild_rule_text(request):
    """The rule text the saved criteria give, for the committee to review and save."""
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        if q_projects.get_project(cur, tender_id) is None:
            return fail("Project not found", 404)
        saved = (q_projects.latest_prompt(cur, tender_id) or {}).get("criteria_block", "")
        return ok(rule_text.rebuilt(cur, tender_id, q_projects.criteria(cur, tender_id), saved))


async def approve_criteria(request):
    check_csrf(request)
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        rows = q_projects.criteria(cur, tender_id)
        problem = missing_max_marks(rows)
        if problem:
            return fail(problem, 409)
        user_id = current_user(request)
        q_prompts.approve_prompt(cur, tender_id, user_id, criteria_edits.snapshot(rows))
        # Bids uploaded before approval are checked now.
        eligibility_actions.queue_checks(cur, tender_id, (user_id, "Criteria approved"))
    return ok(None, "Criteria approved")


routes = [
    Route("/api/v1/projects/{tender_id:uuid}/criteria", criteria_page, methods=["GET"]),
    Route("/api/v1/projects/{tender_id:uuid}/criteria", save_criteria, methods=["POST"]),
    Route("/api/v1/projects/{tender_id:uuid}/criteria/approve", approve_criteria,
          methods=["POST"]),
    Route("/api/v1/projects/{tender_id:uuid}/criteria/rule-text", rebuild_rule_text,
          methods=["GET"]),
]
