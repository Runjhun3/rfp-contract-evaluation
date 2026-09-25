"""Projects list, new project, RFP upload and criteria review."""
from datetime import date

from starlette.routing import Route

from app import files
from app.db import q_projects, q_runs
from app.db.connection import transaction
from app.web.auth import form_with_csrf, local_user
from app.web.common import BadUpload, go, read_pdf_upload, render, stepper


def _db(request):
    return transaction(request.app.state.settings)


async def home(request):
    return go("/projects")


async def list_projects(request):
    user = local_user(request)
    page = max(1, int(request.query_params.get("page", "1") or 1))
    with _db(request) as cur:
        rows = q_projects.list_projects(cur, page)
    return render(request, "projects.html", user, projects=rows[:q_projects.PAGE_SIZE],
                  page=page, more=len(rows) > q_projects.PAGE_SIZE)


async def new_project(request):
    return render(request, "project_new.html", local_user(request), error=None, form={})


async def create_project(request):
    user = local_user(request)
    form = await form_with_csrf(request)
    values = {k: str(form.get(k, "")).strip() for k in ("name", "gem", "department", "due")}
    try:
        date.fromisoformat(values["due"])
    except ValueError:
        return render(request, "project_new.html", user, form=values,
                      error="Enter the final bid closing date as YYYY-MM-DD.")
    if not values["name"]:
        return render(request, "project_new.html", user, form=values, error="Enter a project name.")
    with _db(request) as cur:
        tender_id = q_projects.create_project(cur, values["name"], values["gem"],
                                              values["department"], values["due"], user["user_id"])
    return go(f"/projects/{tender_id}/rfp")


async def open_project(request):
    tender_id = request.path_params["tender_id"]
    with _db(request) as cur:
        project = q_projects.get_project(cur, tender_id)
        run = q_runs.latest_run(cur, tender_id)
    if project is None:
        return go("/projects")
    status = project["status"]
    if status in ("EVALUATING", "REVIEW", "CLOSED") and run:
        return go(f"/runs/{run['run_id']}" + ("/results" if status != "EVALUATING" else ""))
    step = {"DRAFT": "rfp", "PROMPT_APPROVED": "participants"}.get(status, "criteria")
    return go(f"/projects/{tender_id}/{step}")


def _project_context(cur, tender_id: str, current: str) -> dict:
    project = q_projects.get_project(cur, tender_id)
    run = q_runs.latest_run(cur, tender_id)
    return {"project": project, "steps": stepper(project, current, run and run["run_id"])}


async def rfp_page(request, error=None):
    user = local_user(request)
    tender_id = request.path_params["tender_id"]
    with _db(request) as cur:
        ctx = _project_context(cur, tender_id, "rfp")
        ctx["rfp"] = q_projects.latest_rfp(cur, tender_id)
    return render(request, "rfp.html", user, error=error, **ctx)


async def upload_rfp(request):
    user = local_user(request)
    tender_id = request.path_params["tender_id"]
    form = await form_with_csrf(request)
    try:
        name, data, sha, pages = await read_pdf_upload(form)
    except BadUpload as err:
        return await rfp_page(request, error=str(err))
    key = f"tenders/{tender_id}/rfp/{sha}.pdf"
    files.put(request.app.state.settings, key, data)
    with _db(request) as cur:
        doc_id = q_projects.add_rfp(cur, tender_id, name, key, sha, pages, user["user_id"])
        q_runs.enqueue(cur, tender_id, "EXTRACT_CRITERIA", doc_id)
        q_projects.set_status(cur, tender_id, "RFP_UPLOADED")
    return go(f"/projects/{tender_id}/criteria")


async def criteria_page(request):
    user = local_user(request)
    tender_id = request.path_params["tender_id"]
    with _db(request) as cur:
        ctx = _project_context(cur, tender_id, "criteria")
        ctx.update(criteria=q_projects.criteria(cur, tender_id),
                   prompt=q_projects.latest_prompt(cur, tender_id))
    ctx["technical_total"] = sum(c["max_marks"] or 0 for c in ctx["criteria"]
                                 if c["stage"] != "ELIGIBILITY")
    return render(request, "criteria.html", user, **ctx)


async def save_criteria(request):
    tender_id = request.path_params["tender_id"]
    form = await form_with_csrf(request)
    with _db(request) as cur:
        for c in q_projects.criteria(cur, tender_id):
            cid = c["criterion_id"]
            q_projects.update_criterion(cur, cid, {
                "meaning": form.get(f"meaning_{cid}", c["meaning"]),
                "kind": form.get(f"kind_{cid}", c["kind"] or ""),
                "max_marks": form.get(f"max_marks_{cid}") or None,
                "max_items": form.get(f"max_items_{cid}") or None,
                "allowed": [m.strip() for m in str(form.get(f"allowed_{cid}", "")).split(",")
                            if m.strip()],
                "scored_by": form.get(f"scored_by_{cid}", c["scored_by"])})
        q_projects.save_draft_block(cur, tender_id, str(form.get("block", "")))
    return go(f"/projects/{tender_id}/criteria")


async def approve_criteria(request):
    user = local_user(request)
    tender_id = request.path_params["tender_id"]
    await form_with_csrf(request)
    with _db(request) as cur:
        q_projects.approve_prompt(cur, tender_id, user["user_id"])
    return go(f"/projects/{tender_id}/participants")


routes = [
    Route("/", home, methods=["GET"]),
    Route("/projects", list_projects, methods=["GET"]),
    Route("/projects", create_project, methods=["POST"]),
    Route("/projects/new", new_project, methods=["GET"]),
    Route("/projects/{tender_id:uuid}", open_project, methods=["GET"]),
    Route("/projects/{tender_id:uuid}/rfp", rfp_page, methods=["GET"]),
    Route("/projects/{tender_id:uuid}/rfp", upload_rfp, methods=["POST"]),
    Route("/projects/{tender_id:uuid}/criteria", criteria_page, methods=["GET"]),
    Route("/projects/{tender_id:uuid}/criteria", save_criteria, methods=["POST"]),
    Route("/projects/{tender_id:uuid}/criteria/approve", approve_criteria, methods=["POST"]),
]
