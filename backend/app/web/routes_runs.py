"""Start an evaluation, watch its progress (page + JSON for polling)."""
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.db import q_bids, q_projects, q_runs
from app.db.connection import transaction
from app.web.auth import form_with_csrf, need
from app.web.common import go, render, stepper

STAGES = ["READING", "OCR", "LABELLING", "ITEMS", "CHECKS", "SCORING", "DONE"]
STAGE_LABEL = {"QUEUED": "Waiting to start", "READING": "Reading pages",
               "OCR": "Reading scanned pages", "LABELLING": "Finding projects and CVs",
               "ITEMS": "Checking each item", "CHECKS": "Verifying quotes",
               "SCORING": "Scoring", "DONE": "Done", "FAILED": "Failed"}


def _db(request):
    return transaction(request.app.state.settings)


async def start_run(request):
    user = need(request, "EVALUATOR")
    tender_id = str(request.path_params["tender_id"])
    await form_with_csrf(request)
    settings = request.app.state.settings
    with _db(request) as cur:
        prompt = q_projects.latest_prompt(cur, tender_id)
        ready = [s["submission_id"] for s in q_bids.ready_submissions(cur, tender_id)]
        if not prompt or prompt["status"] != "APPROVED" or not ready:
            return go(f"/projects/{tender_id}/participants")
        run_id = q_runs.start_run(cur, tender_id, prompt["prompt_id"], settings.claude_model,
                                  user["user_id"], ready)
    return go(f"/runs/{run_id}")


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
    user = need(request)
    run_id = str(request.path_params["run_id"])
    with _db(request) as cur:
        run = q_runs.get_run(cur, run_id)
        if run is None:
            return go("/projects")
        project = q_projects.get_project(cur, run["tender_id"])
        rows = _rows(cur, run_id)
    return render(request, "run.html", user, project=project, run=run, rows=rows,
                  steps=stepper(project, "evaluate", run_id))


async def run_progress(request):
    need(request)
    run_id = str(request.path_params["run_id"])
    with _db(request) as cur:
        run = q_runs.get_run(cur, run_id)
        rows = _rows(cur, run_id) if run else []
    if run is None:
        return JSONResponse({"data": None, "message": "Run not found"}, status_code=404)
    data = {"status": run["status"],
            "rows": [{k: r[k] for k in ("submission_id", "short_name", "stage", "label",
                                        "percent")} for r in rows]}
    return JSONResponse({"data": data, "message": "ok"})


routes = [
    Route("/projects/{tender_id:uuid}/runs", start_run, methods=["POST"]),
    Route("/runs/{run_id:uuid}", run_page, methods=["GET"]),
    Route("/api/v1/runs/{run_id:uuid}/progress", run_progress, methods=["GET"]),
]
