"""Phase-1 pipeline for ONE bidder: pages -> OCR -> labels -> items -> item calls
-> evidence + copy checks -> criterion calls -> arithmetic check -> scores.
Every step writes JSON into run_dir and is skipped on re-run if already done.
"""
import uuid
from pathlib import Path

from app.config import Settings
from app.evaluate.arithmetic_check import check_criterion
from app.evaluate.copy_check import check_copies
from app.evaluate.criterion_eval import evaluate_criterion
from app.evaluate.document_checks import cited_pages, document_checks
from app.evaluate.document_flags import document_flags
from app.evaluate.evidence_check import check_item
from app.evaluate.flags import review_reasons
from app.forensics.checker import DocumentChecker
from app.evaluate.item_eval import evaluate_item, system_prompt
from app.ingest.build_items import build_items
from app.ingest.prepare import Stage, labelled_pages
from app.llm.client import LlmClient
from app.llm.prompts import versions
from app.schemas.llm import CriterionResult, ItemResult
from app.schemas.records import (CopyGroup, Criterion, CriterionScore, EvidenceCheck, Item,
                                 Page, Requirement, RunContext)
from app.storage import cached, safe_name, sha256_file, write


def run(bid_pdf: Path, ctx: RunContext, criteria: list[Criterion], block: str,
        run_dir: Path, settings: Settings, llm: LlmClient, run_id: str | None = None,
        on_stage: Stage | None = None, requirements: list[Requirement] | None = None,
        pages_dir: Path | None = None) -> list[CriterionScore]:
    """requirements: the tender's eligibility requirements. Pages are labelled with them
    too, exactly as eligibility screening labels them, so the label calls are shared.
    pages_dir: the bid file's shared read and OCR (prepare.file_pages_dir)."""
    stage = on_stage or (lambda name, done=0, total=0: None)
    cached(run_dir / "run.json", dict,
           lambda: _run_meta(bid_pdf, ctx, criteria, block, settings, run_id))
    pages = labelled_pages(bid_pdf, ctx.bidder, criteria, requirements or [], run_dir,
                           settings, llm, stage, pages_dir)
    items = cached(run_dir / "items.json", list[Item],
                   lambda: build_items(pages, {c.code: c.kind for c in criteria}))
    by_no = {p.pdf_page_no: p for p in pages}
    results = _item_results(items, by_no, ctx, system_prompt(ctx, block), bid_pdf, run_dir,
                            llm, stage, {c.code: c for c in criteria})
    stage("CHECKS", len(items), len(items))
    checks = _evidence_checks(items, results, by_no, ctx, settings,
                              (bid_pdf, run_dir, pages_dir or run_dir))
    copies = cached(run_dir / "copy_groups.json", list[CopyGroup],
                    lambda: check_copies(items, results))
    stage("SCORING", len(items), len(items))
    scores = [_score(c, items, results, checks, copies, by_no, ctx, run_dir, settings, llm)
              for c in criteria]
    write(run_dir / "scores.json", scores)
    return scores


def _evidence_checks(items: list[Item], results: dict[str, ItemResult],
                     pages: dict[int, Page], ctx: RunContext, settings: Settings,
                     where: tuple[Path, Path, Path]) -> list[EvidenceCheck]:
    """Python's checks of each item, its document checks among them (D-059), made once:
    the bid's document checker is opened only when the checks are not yet saved, on the
    pages the items cite (D-065). where: the bid PDF, the run folder, the file's shared
    folder."""
    bid_pdf, run_dir, pages_dir = where
    path = run_dir / "evidence_checks.json"
    if path.exists():
        return cached(path, list[EvidenceCheck], list)
    cited = {i.label: cited_pages(results[i.label], i) for i in items if i.label in results}
    checker = DocumentChecker(bid_pdf, pages, settings, pages_dir,
                              [n for pages_cited in cited.values() for n in pages_cited])
    try:
        checks = [c for i in items if i.label in results
                  for c in check_item(results[i.label], i, pages, settings, ctx.bid_due_date)
                  + document_checks(results[i.label], i, pages, settings, ctx.bid_due_date)
                  + document_flags(i.label, cited[i.label], checker, settings)]
    finally:
        checker.close()
    return cached(path, list[EvidenceCheck], lambda: checks)


def _run_meta(bid_pdf: Path, ctx: RunContext, criteria: list[Criterion], block: str,
              settings: Settings, run_id: str | None) -> dict:
    """Snapshot of everything the run depended on (audit + loading into the DB)."""
    return {"run_id": run_id or str(uuid.uuid4()), "context": ctx.model_dump(mode="json"),
            "bid_file": bid_pdf.name, "bid_sha256": sha256_file(bid_pdf),
            "model": settings.claude_model, "prompts": versions(),
            "criteria": [c.model_dump(mode="json") for c in criteria], "criteria_block": block}


def _item_results(items: list[Item], pages: dict[int, Page], ctx: RunContext, system: str,
                  bid_pdf: Path, run_dir: Path, llm: LlmClient, stage: Stage,
                  by_code: dict[str, Criterion]) -> dict[str, ItemResult]:
    results = {}
    for done, item in enumerate(items):
        stage("ITEMS", done, len(items))
        if item.duplicate_of:
            continue                 # another copy of the same CV is scored instead
        results[item.label] = cached(
            run_dir / "items" / f"{safe_name(item.label)}.json", ItemResult,
            lambda item=item, c=by_code.get(item.criterion_code): evaluate_item(
                item, pages, ctx, system, llm, bid_pdf, c.rfp_text if c else "",
                c.count_bands if c else None))
    return results


def _score(criterion: Criterion, items: list[Item], results: dict[str, ItemResult],
           checks: list[EvidenceCheck], copies: list[CopyGroup], pages: dict[int, Page],
           ctx: RunContext, run_dir: Path, settings: Settings, llm: LlmClient) -> CriterionScore:
    mine = {i.label: results[i.label] for i in items
            if i.criterion_code == criterion.code and i.label in results}
    result = cached(run_dir / "criteria" / f"{safe_name(criterion.code)}.json", CriterionResult,
                    lambda: evaluate_criterion(criterion, ctx.bidder, list(mine.values()), llm))
    arith = check_criterion(criterion, result, mine)
    reasons = review_reasons(result, arith, {i.label: i for i in items}, mine, checks,
                             copies, pages, settings)
    duplicates = [f"{i.label} not scored: same CV as {i.duplicate_of}" for i in items
                  if i.criterion_code == criterion.code and i.duplicate_of]
    summary = result.summary if mine else nothing_found(criterion, items)
    return CriterionScore(code=criterion.code, llm_marks=result.marks,
                          checked_marks=arith.checked_marks, arithmetic_ok=arith.ok,
                          needs_review=bool(reasons), review_reasons=reasons,
                          summary="; ".join([summary, *arith.issues, *duplicates]))


def nothing_found(criterion: Criterion, items: list[Item]) -> str:
    """Why a criterion scored 0 with no items: what of that kind the bid does contain,
    and where it went, so the committee can check the mapping (flag NO_ITEMS_FOUND)."""
    if criterion.kind == "BID":
        return (f"No page in the bid was found as evidence for {criterion.code}, so it scores 0. "
                "Check the bid and decide the criterion.")
    word = "CV" if criterion.kind == "CV" else "project"
    elsewhere = [f"p.{i.from_page}-{i.to_page} {i.title or i.label} (assigned to "
                 f"{i.criterion_code})" for i in items
                 if i.kind == criterion.kind and i.criterion_code != criterion.code]
    found = (f" {word[0].upper()}{word[1:]}s found in the bid: {'; '.join(elsewhere)}."
             if elsewhere else f" No {word} pages were found in the bid.")
    return f"No {word} was assigned to {criterion.code}, so it scores 0.{found}"
