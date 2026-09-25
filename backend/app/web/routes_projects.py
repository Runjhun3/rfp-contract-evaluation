"""API: session, projects list, new project, RFP upload and criteria review."""
from datetime import date

from starlette.routing import Route

from app import files
from app.db import q_projects, q_runs
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.web.auth import check_csrf, csrf_token
from app.web.common import BadUpload, fail, ok, read_pdf_upload, stepper

LANDING = {"DRAFT": "rfp", "RFP_UPLOADED": "criteria", "CRITERIA_READY": "criteria",
           "PROMPT_APPROVED": "participants"}


def _db(request):
    return transaction(request.app.state.settings)


async def session(request):
    return ok({"csrf": csrf_token(request), "user": "Local user"})


async def list_projects(request):
    page = max(1, int(request.query_params.get("page", "1") or 1))
    with _db(request) as cur:
        rows = q_projects.list_projects(cur, page)
    return ok({"projects": rows[:q_projects.PAGE_SIZE], "page": page,
               "more": len(rows) > q_projects.PAGE_SIZE})


async def create_project(request):
    check_csrf(request)
    body = await request.json()
    values = {k: str(body.get(k) or "").strip() for k in ("name", "gem", "department", "due")}
    try:
        date.fromisoformat(values["due"])
    except ValueError:
        return fail("Enter the final bid closing date as YYYY-MM-DD.")
    if not values["name"]:
        return fail("Enter a project name.")
    with _db(request) as cur:
        tender_id = q_projects.create_project(cur, values["name"], values["gem"],
                                              values["department"], values["due"], LOCAL_USER_ID)
    return ok({"tender_id": tender_id}, "Project created", 201)


def project_head(cur, tender_id: str, current: str) -> dict | None:
    """Project details + stepper, shared by every project screen."""
    project = q_projects.get_project(cur, tender_id)
    if project is None:
        return None
    run = q_runs.latest_run(cur, tender_id)
    return {"project": project, "steps": stepper(project, current, run and run["run_id"]),
            "latest_run": run}


async def open_project(request):
    """Where to land when a project is opened: the step it has reached."""
    with _db(request) as cur:
        head = project_head(cur, str(request.path_params["tender_id"]), "")
    if head is None:
        return fail("Project not found", 404)
    status, run, base = head["project"]["status"], head["latest_run"], f"/projects/{head['project']['tender_id']}"
    if status in ("EVALUATING", "REVIEW", "CLOSED") and run:
        landing = f"/runs/{run['run_id']}" + ("/results" if status != "EVALUATING" else "")
    else:
        landing = f"{base}/{LANDING.get(status, 'criteria')}"
    return ok({**head, "landing": landing})


async def rfp_page(request):
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        head = project_head(cur, tender_id, "rfp")
        if head is None:
            return fail("Project not found", 404)
        head["rfp"] = q_projects.latest_rfp(cur, tender_id)
    if head["rfp"]:
        head["rfp"].pop("s3_key")
    return ok(head)


async def upload_rfp(request):
    check_csrf(request)
    tender_id = str(request.path_params["tender_id"])
    try:
        name, data, sha, pages = await read_pdf_upload(await request.form())
    except BadUpload as err:
        return fail(str(err))
    key = f"tenders/{tender_id}/rfp/{sha}.pdf"
    files.put(request.app.state.settings, key, data)
    with _db(request) as cur:
        doc_id = q_projects.add_rfp(cur, tender_id, name, key, sha, pages, LOCAL_USER_ID)
        q_runs.enqueue(cur, tender_id, "EXTRACT_CRITERIA", doc_id)
        q_projects.set_status(cur, tender_id, "RFP_UPLOADED")
    return ok({"doc_id": doc_id}, "RFP uploaded; reading criteria", 201)


routes = [
    Route("/api/v1/session", session, methods=["GET"]),
    Route("/api/v1/projects", list_projects, methods=["GET"]),
    Route("/api/v1/projects", create_project, methods=["POST"]),
    Route("/api/v1/projects/{tender_id:uuid}", open_project, methods=["GET"]),
    Route("/api/v1/projects/{tender_id:uuid}/rfp", rfp_page, methods=["GET"]),
    Route("/api/v1/projects/{tender_id:uuid}/rfp", upload_rfp, methods=["POST"]),
]
