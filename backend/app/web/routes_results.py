"""Results matrix, presentation marks, evidence review, decisions, page images."""
from decimal import Decimal, InvalidOperation

from starlette.responses import Response
from starlette.routing import Route

from app.db import q_projects, q_results, q_runs
from app.db.connection import transaction
from app.web.auth import form_with_csrf, local_user
from app.web.common import go, render, stepper
from app.web.page_image import page_png


def _db(request):
    return transaction(request.app.state.settings)


def _matrix(cur, run_id: str, tender_id: str) -> dict:
    codes = q_results.scored_criteria(cur, run_id)
    cells: dict[str, dict] = {}
    for s in q_results.scores(cur, run_id):
        cells.setdefault(s["submission_id"], {})[s["code"]] = s
    pres = q_results.presentation(cur, tender_id)
    pres_marks = q_results.presentation_marks(cur, pres["criterion_id"]) if pres else {}
    rows = []
    for p in q_runs.progress(cur, run_id):
        mine = cells.get(p["submission_id"], {})
        docs = sum((c["marks"] for c in mine.values()), Decimal(0))
        extra = pres_marks.get(p["submission_id"])
        rows.append({"submission_id": p["submission_id"], "name": p["short_name"],
                     "stage": p["stage"], "cells": mine, "docs": docs, "presentation": extra,
                     "total": docs + (extra or 0)})
    rows.sort(key=lambda r: r["total"], reverse=True)
    for i, row in enumerate(rows):
        tied = [r for r in rows if r["total"] == row["total"]]
        row["rank"] = f"{rows.index(tied[0]) + 1}{'=' if len(tied) > 1 else ''}"
    open_reviews = sum(1 for r in rows for c in r["cells"].values()
                       if c["needs_review"] and not c["reviewed"])
    return {"codes": codes, "rows": rows, "presentation": pres, "open_reviews": open_reviews,
            "docs_max": sum((c["max_marks"] or 0 for c in codes), Decimal(0))}


async def results_page(request):
    user = local_user(request)
    run_id = str(request.path_params["run_id"])
    with _db(request) as cur:
        run = q_runs.get_run(cur, run_id)
        if run is None:
            return go("/projects")
        project = q_projects.get_project(cur, run["tender_id"])
        matrix = _matrix(cur, run_id, run["tender_id"])
    return render(request, "results.html", user, project=project, run=run,
                  steps=stepper(project, "results", run_id), **matrix)


async def save_presentation(request):
    user = local_user(request)
    run_id = str(request.path_params["run_id"])
    form = await form_with_csrf(request)
    with _db(request) as cur:
        run = q_runs.get_run(cur, run_id)
        pres = q_results.presentation(cur, run["tender_id"])
        for p in q_runs.progress(cur, run_id):
            raw = str(form.get(f"p_{p['submission_id']}", "")).strip()
            try:
                marks = Decimal(raw)
            except InvalidOperation:
                continue
            if pres and Decimal(0) <= marks <= (pres["max_marks"] or marks):
                q_results.save_presentation(cur, p["submission_id"], pres["criterion_id"], marks,
                                            user["user_id"])
    return go(f"/runs/{run_id}/results")


async def evidence_page(request, error=None):
    user = local_user(request)
    score_id = str(request.path_params["score_id"])
    with _db(request) as cur:
        score = q_results.score_detail(cur, score_id)
        if score is None:
            return go("/projects")
        items = q_results.items(cur, score["run_id"], score["submission_id"], score["criterion_id"])
        chosen = request.query_params.get("item") or (items[0]["item_id"] if items else None)
        item = next((i for i in items if i["item_id"] == chosen), None)
        checks = q_results.checks(cur, item["item_id"]) if item else []
        history = q_results.decisions(cur, score_id)
        project = q_projects.get_project(cur, score["tender_id"])
    page_no = int(request.query_params.get("page") or (item["from_page"] if item else 1))
    return render(request, "evidence.html", user, score=score, items=items, item=item,
                  checks=checks, history=history, project=project, page_no=page_no, error=error)


async def record_decision(request):
    user = local_user(request)
    score_id = str(request.path_params["score_id"])
    form = await form_with_csrf(request)
    reason = str(form.get("reason", "")).strip()
    action = "OVERRIDE" if form.get("action") == "OVERRIDE" else "ACCEPT"
    with _db(request) as cur:
        score = q_results.score_detail(cur, score_id)
    try:
        marks = Decimal(str(form.get("marks"))) if action == "OVERRIDE" else score["checked_marks"]
    except InvalidOperation:
        return await evidence_page(request, error="Enter the overriding marks as a number.")
    if len(reason) < 10 or not (0 <= marks <= (score["max_marks"] or marks)):
        return await evidence_page(request, error="Give a reason of at least 10 characters "
                                                  "and marks within the criterion's maximum.")
    with _db(request) as cur:
        q_results.record_decision(cur, score_id, action, marks, reason, user["user_id"])
    return go(f"/runs/{score['run_id']}/results")


async def page_image(request):
    submission_id = str(request.path_params["submission_id"])
    with _db(request) as cur:
        key = q_results.bid_file_key(cur, submission_id)
    png = page_png(request.app.state.settings, key, int(request.path_params["page"])) if key else None
    if png is None:
        return Response(status_code=404)
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


routes = [
    Route("/runs/{run_id:uuid}/results", results_page, methods=["GET"]),
    Route("/runs/{run_id:uuid}/presentation", save_presentation, methods=["POST"]),
    Route("/scores/{score_id:uuid}", evidence_page, methods=["GET"]),
    Route("/scores/{score_id:uuid}/decision", record_decision, methods=["POST"]),
    Route("/submissions/{submission_id:uuid}/pages/{page:int}.png", page_image, methods=["GET"]),
]
