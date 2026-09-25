"""Participants: pick firms, add a firm, upload or replace each bid."""
from starlette.routing import Route

from app import files
from app.db import q_bids, q_projects, q_runs
from app.db.connection import transaction
from app.web.auth import form_with_csrf, need
from app.web.common import BadUpload, go, read_pdf_upload, render, stepper


def _db(request):
    return transaction(request.app.state.settings)


async def participants_page(request, error=None):
    user = need(request)
    tender_id = str(request.path_params["tender_id"])
    search = request.query_params.get("q", "")
    with _db(request) as cur:
        project = q_projects.get_project(cur, tender_id)
        run = q_runs.latest_run(cur, tender_id)
        subs = q_bids.submissions(cur, tender_id)
        firms = q_bids.bidders(cur, search)
        prompt = q_projects.latest_prompt(cur, tender_id)
    chosen = {s["bidder_id"] for s in subs}
    return render(request, "participants.html", user, project=project, submissions=subs,
                  firms=firms, chosen=chosen, search=search, error=error,
                  steps=stepper(project, "participants", run and run["run_id"]),
                  ready=[s for s in subs if s["file_id"]],
                  approved=bool(prompt and prompt["status"] == "APPROVED"))


async def set_participants(request):
    need(request, "EVALUATOR")
    tender_id = str(request.path_params["tender_id"])
    form = await form_with_csrf(request)
    with _db(request) as cur:
        q_bids.set_participants(cur, tender_id, [str(v) for v in form.getlist("bidder")])
    return go(f"/projects/{tender_id}/participants")


async def add_firm(request):
    need(request, "EVALUATOR")
    tender_id = str(request.path_params["tender_id"])
    form = await form_with_csrf(request)
    legal = str(form.get("legal_name", "")).strip()
    if not legal:
        return await participants_page(request, error="Enter the firm's legal name.")
    with _db(request) as cur:
        bidder_id = q_bids.add_bidder(cur, legal, str(form.get("short_name", "")).strip())
        cur.execute("""insert into bid_submission (tender_id, bidder_id) values (%s, %s)
                       on conflict do nothing""", (tender_id, bidder_id))
    return go(f"/projects/{tender_id}/participants")


async def upload_bid(request):
    user = need(request, "EVALUATOR")
    submission_id = str(request.path_params["submission_id"])
    form = await form_with_csrf(request)
    with _db(request) as cur:
        sub = q_bids.get_submission(cur, submission_id)
    if sub is None:
        return go("/projects")
    request.path_params["tender_id"] = sub["tender_id"]
    try:
        name, data, sha, pages = await read_pdf_upload(form)
    except BadUpload as err:
        return await participants_page(request, error=f"{sub['short_name']}: {err}")
    key = f"tenders/{sub['tender_id']}/bids/{submission_id}/{sha}.pdf"
    files.put(request.app.state.settings, key, data)
    with _db(request) as cur:
        q_bids.add_file(cur, submission_id, name, key, sha, pages, user["user_id"])
    return go(f"/projects/{sub['tender_id']}/participants")


routes = [
    Route("/projects/{tender_id:uuid}/participants", participants_page, methods=["GET"]),
    Route("/projects/{tender_id:uuid}/participants", set_participants, methods=["POST"]),
    Route("/projects/{tender_id:uuid}/firms", add_firm, methods=["POST"]),
    Route("/submissions/{submission_id:uuid}/file", upload_bid, methods=["POST"]),
]
