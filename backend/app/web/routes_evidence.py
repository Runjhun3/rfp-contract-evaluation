"""API: one criterion score's evidence, the committee decision, and bid page images."""
from decimal import Decimal, InvalidOperation

from starlette.responses import Response
from starlette.routing import Route

from app.db import q_projects, q_results
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.web.auth import check_csrf
from app.web.common import fail, ok
from app.web.page_image import page_png


def _db(request):
    return transaction(request.app.state.settings)


async def evidence_page(request):
    score_id = str(request.path_params["score_id"])
    with _db(request) as cur:
        score = q_results.score_detail(cur, score_id)
        if score is None:
            return fail("Score not found", 404)
        items = q_results.items(cur, score["run_id"], score["submission_id"], score["criterion_id"])
        chosen = request.query_params.get("item") or (items[0]["item_id"] if items else None)
        item = next((i for i in items if i["item_id"] == chosen), None)
        checks = q_results.checks(cur, item["item_id"]) if item else []
        history = q_results.decisions(cur, score_id)
        project = q_projects.get_project(cur, score["tender_id"])
    return ok({"score": score, "items": items, "item": item, "checks": checks,
               "history": history, "project": project})


def _decision(body: dict, score: dict) -> tuple[str, Decimal, str] | str:
    """(action, marks, reason), or an error message for the reviewer."""
    reason = str(body.get("reason") or "").strip()
    action = "OVERRIDE" if body.get("action") == "OVERRIDE" else "ACCEPT"
    try:
        marks = Decimal(str(body.get("marks"))) if action == "OVERRIDE" else score["checked_marks"]
    except InvalidOperation:
        return "Enter the overriding marks as a number."
    if len(reason) < 10 or not (0 <= marks <= (score["max_marks"] or marks)):
        return "Give a reason of at least 10 characters and marks within the criterion's maximum."
    return action, marks, reason


async def record_decision(request):
    check_csrf(request)
    score_id = str(request.path_params["score_id"])
    body = await request.json()
    with _db(request) as cur:
        score = q_results.score_detail(cur, score_id)
    if score is None:
        return fail("Score not found", 404)
    decision = _decision(body, score)
    if isinstance(decision, str):
        return fail(decision)
    with _db(request) as cur:
        q_results.record_decision(cur, score_id, *decision, LOCAL_USER_ID)
    return ok({"run_id": score["run_id"]}, "Decision recorded", 201)


async def page_image(request):
    submission_id = str(request.path_params["submission_id"])
    with _db(request) as cur:
        key = q_results.bid_file_key(cur, submission_id)
    png = page_png(request.app.state.settings, key, int(request.path_params["page"])) if key else None
    if png is None:
        return Response(status_code=404)
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


routes = [
    Route("/api/v1/scores/{score_id:uuid}", evidence_page, methods=["GET"]),
    Route("/api/v1/scores/{score_id:uuid}/decision", record_decision, methods=["POST"]),
    Route("/api/v1/submissions/{submission_id:uuid}/pages/{page:int}.png", page_image,
          methods=["GET"]),
]
