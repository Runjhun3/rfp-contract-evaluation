"""API: results matrix (ranked) and the committee's presentation marks."""
from decimal import Decimal, InvalidOperation

from starlette.routing import Route

from app.db import q_projects, q_results, q_runs
from app.db.connection import transaction
from app.db.repo_setup import LOCAL_USER_ID
from app.web.auth import check_csrf
from app.web.common import fail, ok, stepper


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
    for row in rows:
        tied = [r for r in rows if r["total"] == row["total"]]
        row["rank"] = f"{rows.index(tied[0]) + 1}{'=' if len(tied) > 1 else ''}"
    open_reviews = sum(1 for r in rows for c in r["cells"].values()
                       if c["needs_review"] and not c["reviewed"])
    return {"codes": codes, "rows": rows, "presentation": pres, "open_reviews": open_reviews,
            "docs_max": sum((c["max_marks"] or 0 for c in codes), Decimal(0))}


async def results_page(request):
    run_id = str(request.path_params["run_id"])
    with _db(request) as cur:
        run = q_runs.get_run(cur, run_id)
        if run is None:
            return fail("Run not found", 404)
        project = q_projects.get_project(cur, run["tender_id"])
        matrix = _matrix(cur, run_id, run["tender_id"])
    return ok({"project": project, "run": run, "steps": stepper(project, "results", run_id),
               **matrix})


def _parse_marks(raw: dict, limit: Decimal | None) -> dict[str, Decimal] | None:
    """Blank entries are skipped; any other bad value rejects the whole save."""
    out = {}
    for submission_id, value in raw.items():
        text = str(value if value is not None else "").strip()
        if not text:
            continue
        try:
            marks = Decimal(text)
        except InvalidOperation:
            return None
        if not Decimal(0) <= marks <= (limit if limit is not None else marks):
            return None
        out[str(submission_id)] = marks
    return out


async def save_presentation(request):
    check_csrf(request)
    run_id = str(request.path_params["run_id"])
    body = await request.json()
    with _db(request) as cur:
        run = q_runs.get_run(cur, run_id)
        pres = q_results.presentation(cur, run["tender_id"]) if run else None
        if pres is None:
            return fail("This run has no presentation criterion.", 404)
        marks = _parse_marks(body.get("marks") or {}, pres["max_marks"])
        if marks is None:
            return fail(f"Presentation marks must be numbers from 0 to {pres['max_marks']}.")
        known = {p["submission_id"] for p in q_runs.progress(cur, run_id)}
        for submission_id, value in marks.items():
            if submission_id in known:
                q_results.save_presentation(cur, submission_id, pres["criterion_id"], value,
                                            LOCAL_USER_ID)
    return ok(None, "Presentation marks saved")


routes = [
    Route("/api/v1/runs/{run_id:uuid}/results", results_page, methods=["GET"]),
    Route("/api/v1/runs/{run_id:uuid}/presentation", save_presentation, methods=["POST"]),
]
