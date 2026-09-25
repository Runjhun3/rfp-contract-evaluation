"""API: pick firms, add a firm, upload or replace each bid."""
from starlette.routing import Route

from app import files
from app.db import q_bids, q_projects
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.web.auth import check_csrf
from app.web.common import BadUpload, fail, ok, read_pdf_upload
from app.web.routes_projects import project_head


def _db(request):
    return transaction(request.app.state.settings)


async def participants_page(request):
    tender_id = str(request.path_params["tender_id"])
    with _db(request) as cur:
        head = project_head(cur, tender_id, "participants")
        if head is None:
            return fail("Project not found", 404)
        subs = q_bids.submissions(cur, tender_id)
        firms = q_bids.bidders(cur, request.query_params.get("q", ""))
        prompt = q_projects.latest_prompt(cur, tender_id)
    for s in subs:
        s.pop("s3_key")
    return ok({**head, "submissions": subs, "firms": firms,
               "ready": sum(1 for s in subs if s["file_id"]),
               "approved": bool(prompt and prompt["status"] == "APPROVED")})


async def set_participants(request):
    check_csrf(request)
    body = await request.json()
    with _db(request) as cur:
        q_bids.set_participants(cur, str(request.path_params["tender_id"]),
                                [str(v) for v in body.get("bidder_ids", [])])
    return ok(None, "Participants saved")


async def add_firm(request):
    check_csrf(request)
    tender_id = str(request.path_params["tender_id"])
    body = await request.json()
    legal = str(body.get("legal_name") or "").strip()
    if not legal:
        return fail("Enter the firm's legal name.")
    with _db(request) as cur:
        bidder_id = q_bids.add_bidder(cur, legal, str(body.get("short_name") or "").strip())
        cur.execute("""insert into bid_submission (tender_id, bidder_id) values (%s, %s)
                       on conflict do nothing""", (tender_id, bidder_id))
    return ok({"bidder_id": bidder_id}, "Firm added", 201)


async def upload_bid(request):
    check_csrf(request)
    submission_id = str(request.path_params["submission_id"])
    with _db(request) as cur:
        sub = q_bids.get_submission(cur, submission_id)
    if sub is None:
        return fail("Participant not found", 404)
    try:
        name, data, sha, pages = await read_pdf_upload(await request.form())
    except BadUpload as err:
        return fail(f"{sub['short_name']}: {err}")
    key = f"tenders/{sub['tender_id']}/bids/{submission_id}/{sha}.pdf"
    files.put(request.app.state.settings, key, data)
    with _db(request) as cur:
        q_bids.add_file(cur, submission_id, name, key, sha, pages, LOCAL_USER_ID)
    return ok(None, "Bid uploaded", 201)


routes = [
    Route("/api/v1/projects/{tender_id:uuid}/participants", participants_page, methods=["GET"]),
    Route("/api/v1/projects/{tender_id:uuid}/participants", set_participants, methods=["POST"]),
    Route("/api/v1/projects/{tender_id:uuid}/firms", add_firm, methods=["POST"]),
    Route("/api/v1/submissions/{submission_id:uuid}/file", upload_bid, methods=["POST"]),
]
