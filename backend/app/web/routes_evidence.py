"""API: one criterion score's evidence, the committee decision, and bid page images."""
from starlette.responses import Response
from starlette.routing import Route

from app.db import q_results
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.evidence_view import evidence_view
from app.review import decide
from app.web.auth import check_csrf
from app.web.common import fail, ok
from app.web.page_image import page_png


def _db(request):
    return transaction(request.app.state.settings)


async def evidence_page(request):
    with _db(request) as cur:
        view = evidence_view(cur, str(request.path_params["score_id"]),
                             request.query_params.get("item"),
                             request.app.state.settings.review_confidence)
    return ok(view) if view else fail("Score not found", 404)


async def record_decision(request):
    check_csrf(request)
    body = await request.json()
    with _db(request) as cur:
        problem = decide(cur, str(request.path_params["score_id"]), body, LOCAL_USER_ID)
    if problem:
        return fail(problem, 404 if problem == "Score not found" else 400)
    return ok(None, "Decision recorded", 201)


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
