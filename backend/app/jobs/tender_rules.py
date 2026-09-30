"""A tender's criteria as the worker uses them: the criteria the AI scores, and the
eligibility requirements it checks. Evaluation and eligibility screening both label
pages with exactly these lists, so the label calls are shared."""
from app.criteria import SCREENED, scoring
from app.schemas.records import Criterion, Requirement


def scored(rows: list[dict]) -> tuple[list[Criterion], dict[str, str]]:
    """Every criterion with marks the AI scores, and criterion id by code."""
    ways = scoring(rows)
    mine = [{**r, "kind": ways[r["code"]]} for r in rows
            if ways.get(r["code"]) in ("PROJECT", "CV", "BID")]
    criteria = [Criterion(code=r["code"], title=r["title"], meaning=r["meaning"],
                          kind=r["kind"], rfp_text=r["rfp_text"], max_marks=r["max_marks"],
                          max_items=r["max_items"],
                          allowed_item_marks=r["allowed_item_marks"] or [],
                          count_bands=r["count_bands"] or [])
                for r in mine]
    return criteria, {r["code"]: r["criterion_id"] for r in mine}


def requirements(rows: list[dict]) -> list[Requirement]:
    """What screening checks: eligibility criteria and required documents, in code order."""
    return [Requirement(criterion_id=r["criterion_id"], code=r["code"], title=r["title"],
                        meaning=r["meaning"], rfp_text=r["rfp_text"] or "", proof=r["proof"])
            for r in rows if r["stage"] in SCREENED]
