"""CHECK_ELIGIBILITY job: check one bid's latest file against every eligibility
requirement of its tender, and save one check per requirement.

The bid is read, OCR'd and labelled exactly as the evaluation does it (ingest/prepare.py),
into a folder per bid file, set of requirements and label prompt, so a changed
requirement or prompt is labelled afresh while an unchanged bid reuses its saved pages.
The pages each answer quotes its facts from get their document checks with it (D-059,
D-062), so its result includes them; they are shown and decided with the check, never
on their own.
"""
import hashlib
from pathlib import Path

from app import files
from app.config import Settings
from app.db import q_eligibility, q_projects
from app.db.connection import transaction
from app.evaluate.document_flags import document_flags
from app.evaluate.eligibility_check import check_requirement, cited_pages, verify
from app.evaluate.item_eval import system_prompt
from app.forensics.checker import DocumentChecker
from app.ingest.label_pages import criteria_list, eligibility_list
from app.ingest.prepare import file_pages_dir, labelled_pages
from app.jobs import tender_rules
from app.llm.client import LlmClient
from app.llm.prompts import versions
from app.schemas.llm import EligibilityResult
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
    answers = [(req, *check_requirement(req, ctx.bidder, pages, system_prompt(ctx, ""), llm))
               for req in requirements]
    # Only the pages the answers cite are analysed for the document checks (D-065).
    checker = DocumentChecker(files.local_path(settings, bid["s3_key"]), pages, settings,
                              file_pages_dir(settings, bid["file_id"]),
                              [n for _, r, tagged in answers for n in cited_pages(r, tagged)])
    try:
        checks = [_check(req, result, tagged, ctx, pages, settings, checker)
                  for req, result, tagged in answers]
    finally:
        checker.close()
    with transaction(settings) as cur:
        for check in checks:
            q_eligibility.save_check(cur, bid["tender_id"], submission_id, bid["file_id"],
                                     check, versions()["eligibility"], settings.claude_model)


def _pages(settings: Settings, llm: LlmClient, bid: dict, submission_id: str,
           rows: list[dict], requirements: list[Requirement]) -> dict[int, Page]:
    criteria, _ = tender_rules.scored(rows)
    # What the labels depend on: a changed requirement or label prompt labels afresh.
    labels_for = (f"{versions()['label']}\n{criteria_list(criteria)}\n"
                  f"{eligibility_list(requirements)}")
    work_dir = (Path(settings.runs_dir) / "eligibility" / submission_id / bid["file_id"]
                / hashlib.sha256(labels_for.encode()).hexdigest()[:12])
    pages = labelled_pages(files.local_path(settings, bid["s3_key"]), bid["short_name"],
                           criteria, requirements, work_dir, settings, llm,
                           lambda name, done=0, total=0: None,
                           file_pages_dir(settings, bid["file_id"]))
    return {p.pdf_page_no: p for p in pages}


def _check(req: Requirement, result: EligibilityResult, tagged: list[int], ctx: RunContext,
           pages: dict[int, Page], settings: Settings, checker: DocumentChecker) -> dict:
    """The AI's answer with Python's checks of it, its document checks among them."""
    verification = (verify(result, tagged, pages, settings, ctx.bid_due_date)
                    + document_flags(req.code, cited_pages(result, tagged), checker, settings))
    return {"criterion_id": req.criterion_id, "result": result.result,
            "finding": result.finding, "pages": tagged,
            "facts": {k: v.model_dump() for k, v in result.facts.items() if v},
            "verification": [c.model_dump() for c in verification]}
