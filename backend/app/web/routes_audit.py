"""API: the records on screen (see app/audit_view.py): a project's committee decisions,
for every account; a project's activity log and the central one, for administrators."""
from datetime import datetime
from zoneinfo import ZoneInfo

from starlette.responses import Response
from starlette.routing import Route

from app.audit_view import activity, activity_rows, approvals, decision_log, wanted
from app.config import TIMEZONE
from app.db import q_activity, q_events, q_projects
from app.db.connection import transaction
from app.export.activity_csv import activity_csv, file_name
from app.web.auth import current_user, is_admin
from app.web.common import fail, ok
from app.web.routes_projects import project_head

ADMINS_ONLY = "Only an administrator can see the activity log."


async def decisions_page(request):
    tender_id = str(request.path_params["tender_id"])
    with transaction(request.app.state.settings) as cur:
        head = project_head(cur, tender_id, "")       # not a step: none is current
        if head is None:
            return fail("Project not found", 404)
        return ok({**head, **decision_log(cur, tender_id)})


async def activity_page(request):
    if not is_admin(request):
        return fail(ADMINS_ONLY, 403)
    tender_id = str(request.path_params["tender_id"])
    with transaction(request.app.state.settings) as cur:
        head = project_head(cur, tender_id, "")
        if head is None:
            return fail("Project not found", 404)
        return ok({**head, **activity(cur, tender_id, wanted(request.query_params, tender_id)),
                   "approvals": approvals(cur, tender_id)})


async def central_page(request):
    """Every action by every account, across projects, with accounts and sign-ins."""
    if not is_admin(request):
        return fail(ADMINS_ONLY, 403)
    with transaction(request.app.state.settings) as cur:
        return ok(activity(cur, None, wanted(request.query_params, None)))


async def activity_file(request):
    """The log as a CSV file, with the same filters as the page and every matching row
    (not one page). The download itself goes on the log."""
    if not is_admin(request):
        return fail(ADMINS_ONLY, 403)
    tender_id = request.path_params.get("tender_id")
    tender_id = str(tender_id) if tender_id else None
    with transaction(request.app.state.settings) as cur:
        project = q_projects.get_project(cur, tender_id) if tender_id else None
        if tender_id and project is None:
            return fail("Project not found", 404)
        rows = activity_rows(cur, tender_id, wanted(request.query_params, tender_id), None)
        today = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()
        name = file_name(project and project["name"], today)
        q_events.add(cur, tender_id, current_user(request), q_activity.LOG_DOWNLOADED, name,
                     {"note": f"{len(rows)} rows"})
    return Response(activity_csv(rows), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


routes = [Route("/api/v1/projects/{tender_id:uuid}/decisions", decisions_page, methods=["GET"]),
          Route("/api/v1/projects/{tender_id:uuid}/audit", activity_page, methods=["GET"]),
          Route("/api/v1/projects/{tender_id:uuid}/audit.csv", activity_file, methods=["GET"]),
          Route("/api/v1/activity", central_page, methods=["GET"]),
          Route("/api/v1/activity.csv", activity_file, methods=["GET"])]
