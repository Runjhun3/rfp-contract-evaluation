"""API: eligibility screening (the grid, checking again) and one firm's checks with the
committee's decision."""
from starlette.routing import Route

from app import eligibility, eligibility_actions
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.eligibility_view import firm_page
from app.web.auth import check_csrf
from app.web.common import fail, ok
from app.web.routes_projects import project_head


def _db(request):
    return transaction(request.app.state.settings)


async def screening_page(request):
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        head = project_head(cur, tender_id, "eligibility")
        if head is None:
            return fail("Project not found", 404)
        head.update(eligibility.overview(cur, tender_id))
    return ok(head)


async def check_again(request):
    check_csrf(request)
    with _db(request) as cur:
        problem = eligibility_actions.start(cur, str(request.path_params["tender_id"]))
    return fail(problem, 409) if problem else ok(None, "Eligibility check started", 202)


async def check_page(request):
    with _db(request) as cur:
        view = firm_page(cur, str(request.path_params["check_id"]))
    return ok(view) if view else fail("Check not found", 404)


async def record_decision(request):
    check_csrf(request)
    body = await request.json()
    with _db(request) as cur:
        problem = eligibility_actions.decide(cur, str(request.path_params["check_id"]), body,
                                     LOCAL_USER_ID)
    if problem:
        return fail(problem, 404 if problem == "Check not found" else 400)
    return ok(None, "Decision recorded", 201)


routes = [
    Route("/api/v1/projects/{tender_id:uuid}/eligibility", screening_page, methods=["GET"]),
    Route("/api/v1/projects/{tender_id:uuid}/eligibility", check_again, methods=["POST"]),
    Route("/api/v1/eligibility/{check_id:uuid}", check_page, methods=["GET"]),
    Route("/api/v1/eligibility/{check_id:uuid}/decision", record_decision, methods=["POST"]),
]
