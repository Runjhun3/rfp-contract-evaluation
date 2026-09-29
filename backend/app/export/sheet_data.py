"""Everything the committee sheet shows, gathered once: the project, its results
(each participant's latest finished evaluation, ranked), the
criteria in order, every item claimed and every committee decision.
"""
from app.db import q_projects, q_results
from app.results import project_results


def sheet_data(cur, tender_id: str) -> dict | None:
    project = q_projects.get_project(cur, tender_id)
    if project is None:
        return None
    results = project_results(cur, tender_id)
    done = [a for a in q_results.latest_attempts(cur, tender_id) if a["stage"] == "DONE"]
    items = q_results.export_items(cur, [a["run_id"] for a in done],
                                   [a["submission_id"] for a in done])
    names = {r["submission_id"]: r["name"] for r in results["rows"]}
    scores = {c["score_id"]: (r["name"], code) for r in results["rows"]
              for code, c in r["cells"].items()}
    decisions = [{**d, "participant": scores[d["score_id"]][0], "code": scores[d["score_id"]][1]}
                 for d in q_results.export_decisions(cur, list(scores))]
    return {"project": project, "results": results,
            "criteria": [c for c in q_projects.criteria(cur, tender_id)
                         if c["stage"] != "ELIGIBILITY"],
            "items": [{**i, "participant": names.get(i["submission_id"], "")} for i in items],
            "decisions": decisions}
