"""Everything the committee sheet shows, gathered once: the project, its results
(each participant's latest finished evaluation, ranked), the eligibility requirements
and the criteria in order, and for each participant its eligibility checks, its items
and every committee decision.
"""
from app.criteria import SCREENED, group_codes
from app.db import q_eligibility, q_projects, q_results
from app.eligibility import requirements
from app.results import project_results

# A check in words: an eligibility criterion is met or not; a document submitted or not.
WORDS = {"ELIGIBILITY": {"MET": "met", "NOT_MET": "not met", "UNSURE": "unsure"},
         "DOCUMENT": {"MET": "submitted", "NOT_MET": "not submitted", "UNSURE": "unsure"}}


def sheet_data(cur, tender_id: str) -> dict | None:
    project = q_projects.get_project(cur, tender_id)
    if project is None:
        return None
    results = project_results(cur, tender_id)
    done = [a for a in q_results.latest_attempts(cur, tender_id) if a["stage"] == "DONE"]
    items = q_results.export_items(cur, [a["run_id"] for a in done],
                                   [a["submission_id"] for a in done])
    scores = {c["score_id"]: (r["submission_id"], code) for r in results["rows"]
              for code, c in r["cells"].items()}
    decisions = [{**d, "submission_id": scores[d["score_id"]][0],
                  "code": scores[d["score_id"]][1]}
                 for d in q_results.export_decisions(cur, list(scores))]
    checks = q_eligibility.current(cur, tender_id)
    log = q_eligibility.decisions(cur, tender_id)

    def mine(rows: list[dict], row: dict) -> list[dict]:
        return [x for x in rows if x["submission_id"] == row["submission_id"]]

    firms = [{"row": r, "items": mine(items, r), "decisions": mine(decisions, r),
              "eligibility": mine(checks, r), "eligibility_log": mine(log, r)}
             for r in results["rows"]]                          # in rank order
    return {"project": project, "results": results, "firms": firms,
            "requirements": requirements(cur, tender_id),
            "criteria": [c for c in q_projects.criteria(cur, tender_id)
                         if c["stage"] not in SCREENED]}


def eligibility_word(check: dict | None) -> str:
    """A check as the sheet shows it: the committee's decision, else the AI's result."""
    if check is None:
        return "not checked"
    words = WORDS[check["stage"]]
    if check["decision"]:
        return words[check["decision"]]
    return f"not decided (AI: {words[check['result']]})"


def criterion_marks(criterion: dict, row: dict, criteria: list[dict]):
    """A participant's final marks on one criterion: the committee's entry, the scored
    marks, or for a group heading the sum of its sub-criteria (None when none has any)."""
    if criterion["code"] in group_codes(criteria):
        parts = [m for c in criteria if c.get("parent_code") == criterion["code"]
                 if (m := criterion_marks(c, row, criteria)) is not None]
        return sum(parts) if parts else None
    if criterion["criterion_id"] in row["manual"]:          # entered by the committee
        return row["manual"][criterion["criterion_id"]]
    return (row["cells"].get(criterion["code"]) or {}).get("marks")
