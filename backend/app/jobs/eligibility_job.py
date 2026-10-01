"""CHECK_ELIGIBILITY job: check one bid's latest file against every eligibility
requirement of its tender, and save one check per requirement.

The bid is read, OCR'd and labelled exactly as the evaluation does it (ingest/prepare.py),
into a folder per bid file and set of requirements, so a changed requirement is
labelled afresh while an unchanged bid reuses its saved pages.
"""
import hashlib
from pathlib import Path

from app import files
from app.config import Settings
from app.db import q_eligibility, q_projects
from app.db.connection import transaction
from app.evaluate.eligibility_check import check_requirement, verify
from app.evaluate.item_eval import system_prompt
from app.ingest.label_pages import criteria_list, eligibility_list
from app.ingest.prepare import labelled_pages
from app.jobs import tender_rules
from app.llm.client import LlmClient
from app.llm.prompts import versions
from app.schemas.records import Page, Requirement, RunContext


def check_eligibility(settings: Settings, llm: LlmClient, job: dict) -> None:
    submission_id = job["ref_id"]
    with transaction(settings) as cur:
        bid = q_eligibility.subject(cur, submission_id)
        rows = q_projects.criterion_rows(cur, bid["tender_id"]) if bid else []
    requirements = tender_rules.requirements(rows)
    if bid is None or not requirements:
        return                          # no bid file, or nothing to check
    pages = _pages(settings, llm, bid, submission_id, rows, requirements)
    ctx = RunContext(tender_no=bid["gem_bid_no"] or bid["name"], department=bid["department"],
                     bidder=bid["short_name"], bid_due_date=bid["due"])
    checks = [_check(req, ctx, pages, settings, llm) for req in requirements]
    with transaction(settings) as cur:
        for check in checks:
            q_eligibility.save_check(cur, bid["tender_id"], submission_id, bid["file_id"],
                                     check, versions()["eligibility"], settings.claude_model)


def _pages(settings: Settings, llm: LlmClient, bid: dict, submission_id: str,
           rows: list[dict], requirements: list[Requirement]) -> dict[int, Page]:
    criteria, _ = tender_rules.scored(rows)
    labels_for = f"{criteria_list(criteria)}\n{eligibility_list(requirements)}"
    work_dir = (Path(settings.runs_dir) / "eligibility" / submission_id / bid["file_id"]
                / hashlib.sha256(labels_for.encode()).hexdigest()[:12])
    pages = labelled_pages(files.local_path(settings, bid["s3_key"]), bid["short_name"],
                           criteria, requirements, work_dir, settings, llm,
                           lambda name, done=0, total=0: None)
    return {p.pdf_page_no: p for p in pages}


def _check(req: Requirement, ctx: RunContext, pages: dict[int, Page], settings: Settings,
           llm: LlmClient) -> dict:
    result, tagged = check_requirement(req, ctx.bidder, pages, system_prompt(ctx, ""), llm)
    verification = verify(result, tagged, pages, settings, ctx.bid_due_date)
    return {"criterion_id": req.criterion_id, "result": result.result,
            "finding": result.finding, "pages": tagged,
            "facts": {k: v.model_dump() for k, v in result.facts.items() if v},
            "verification": [c.model_dump() for c in verification]}
