"""API: start an evaluation and watch its progress (the page polls GET /runs/{id})."""
from starlette.routing import Route

from app import eligibility
from app.criteria import missing_max_marks
from app.db import q_projects, q_runs
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.web.auth import check_csrf
from app.web.common import fail, ok, stepper

STAGES = ["READING", "OCR", "LABELLING", "ITEMS", "CHECKS", "SCORING", "DONE"]
STAGE_LABEL = {"QUEUED": "Waiting to start", "READING": "Reading pages",
               "OCR": "Reading scanned pages", "LABELLING": "Finding projects and CVs",
               "ITEMS": "Checking each item", "CHECKS": "Verifying quotes",
               "SCORING": "Scoring", "DONE": "Done", "FAILED": "Failed"}


def _db(request):
    return transaction(request.app.state.settings)


async def start_run(request):
    check_csrf(request)
    tender_id = str(request.path_params["tender_id"])
    settings = request.app.state.settings
    with _db(request) as cur:
        prompt = q_projects.latest_prompt(cur, tender_id)
        # Only firms the committee found eligible (every firm with a bid when the
        # tender has no eligibility criteria).
        ready = [f["submission_id"] for f in eligibility.qualified(cur, tender_id)]
        if not prompt or prompt["status"] != "APPROVED":
            return fail("Criteria must be approved first.", 409)
        if not ready:
            return fail("No firm is qualified yet. Upload the bids and decide their "
                        "eligibility checks first.", 409)
        problem = missing_max_marks(q_projects.criteria(cur, tender_id))
        if problem:
            return fail(problem, 409)
        run_id = q_runs.start_run(cur, tender_id, prompt["prompt_id"], settings.claude_model,
                                  LOCAL_USER_ID, ready)
    return ok({"run_id": run_id}, "Evaluation started", 201)


def _rows(cur, run_id: str) -> list[dict]:
    rows = q_runs.progress(cur, run_id)
    for row in rows:
        reached = STAGES.index(row["stage"]) if row["stage"] in STAGES else -1
        row["label"] = STAGE_LABEL.get(row["stage"], row["stage"])
        row["percent"] = 100 if row["stage"] == "DONE" else max(0, round(100 * reached / 6))
        if row["stage"] == "ITEMS" and row["items_total"]:
            row["label"] = f"Checking item {row['items_done'] + 1} of {row['items_total']}"
    return rows


async def run_page(request):
    run_id = str(request.path_params["run_id"])
    with _db(request) as cur:
        run = q_runs.get_run(cur, run_id)
        if run is None:
            return fail("Run not found", 404)
        project = q_projects.get_project(cur, run["tender_id"])
        if project is None:                           # the project was deleted
            return fail("Run not found", 404)
        rows = _rows(cur, run_id)
        ready = q_runs.has_results(cur, run["tender_id"])
        left_out = eligibility.left_out(cur, run["tender_id"],
                                        {r["submission_id"] for r in rows})
    return ok({"project": project, "run": run, "rows": rows,
               "left_out": left_out,
               "steps": stepper(project, "evaluate", run_id, results_ready=ready)})


routes = [
    Route("/api/v1/projects/{tender_id:uuid}/runs", start_run, methods=["POST"]),
    Route("/api/v1/runs/{run_id:uuid}", run_page, methods=["GET"]),
]
