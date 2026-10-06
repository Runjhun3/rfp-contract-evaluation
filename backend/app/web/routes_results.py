"""API: a project's results (latest evaluation of each participant, ranked), the
marks the committee enters itself (e.g. a presentation), and the exported sheet."""
from starlette.responses import Response
from starlette.routing import Route

from app.db.connection import transaction
from app.export.annexure_sheet import build_workbook, file_name
from app.export.sheet_data import sheet_data
from app.results import project_results
from app.review import save_committee_marks as save_marks
from app.web.auth import check_csrf, current_user
from app.web.common import fail, ok
from app.web.routes_projects import project_head


def _db(request):
    return transaction(request.app.state.settings)


async def results_page(request):
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        head = project_head(cur, tender_id, "results")
        if head is None:
            return fail("Project not found", 404)
        return ok({**head, **project_results(cur, tender_id)})


async def save_committee_marks(request):
    check_csrf(request)
    body = await request.json()
    with _db(request) as cur:
        problem = save_marks(cur, str(request.path_params["tender_id"]), body.get("marks"),
                             str(body.get("reason") or ""), current_user(request))
    return fail(problem) if problem else ok(None, "Committee marks saved")


async def export_sheet(request):
    """The Excel sheet; refused (409, with the reasons) until every participant has a
    finished evaluation, every mark is approved and every committee mark is entered."""
    with _db(request) as cur:
        data = sheet_data(cur, str(request.path_params["tender_id"]))
    if data is None:
        return fail("Project not found", 404)
    if data["results"]["export_blockers"]:
        return fail(" ".join(data["results"]["export_blockers"]), 409)
    return Response(build_workbook(data), headers={
        "Content-Disposition": f'attachment; filename="{file_name(data["project"])}"'},
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


routes = [
    Route("/api/v1/projects/{tender_id:uuid}/results", results_page, methods=["GET"]),
    Route("/api/v1/projects/{tender_id:uuid}/committee-marks", save_committee_marks,
          methods=["POST"]),
    Route("/api/v1/projects/{tender_id:uuid}/export.xlsx", export_sheet, methods=["GET"]),
]
