"""Phase-1 pipeline for ONE bidder: pages -> OCR -> labels -> items -> item calls
-> evidence + copy checks -> criterion calls -> arithmetic check -> scores.
Every step writes JSON into run_dir and is skipped on re-run if already done.
"""
import uuid
from pathlib import Path
from typing import Callable

from app.config import Settings
from app.evaluate.arithmetic_check import check_criterion
from app.evaluate.copy_check import check_copies
from app.evaluate.criterion_eval import evaluate_criterion
from app.evaluate.evidence_check import check_item
from app.evaluate.flags import review_reasons
from app.evaluate.item_eval import evaluate_item, system_prompt
from app.ingest.build_items import build_items
from app.ingest.label_pages import label_pages
from app.ingest.ocr import ocr_pages
from app.ingest.read_pages import read_pages
from app.llm.client import LlmClient
from app.llm.prompts import versions
from app.schemas.llm import CriterionResult, ItemResult
from app.schemas.records import (CopyGroup, Criterion, CriterionScore, EvidenceCheck, Item,
                                 Page, RunContext)
from app.storage import cached, safe_name, sha256_file, write

Stage = Callable[..., None]   # stage(name, done=0, total=0)


def run(bid_pdf: Path, ctx: RunContext, criteria: list[Criterion], block: str,
        run_dir: Path, settings: Settings, llm: LlmClient, run_id: str | None = None,
        on_stage: Stage | None = None) -> list[CriterionScore]:
    stage = on_stage or (lambda name, done=0, total=0: None)
    cached(run_dir / "run.json", dict,
           lambda: _run_meta(bid_pdf, ctx, criteria, block, settings, run_id))
    stage("READING")
    pages = cached(run_dir / "pages_text.json", list[Page], lambda: read_pages(bid_pdf))
    stage("OCR")
    pages = cached(run_dir / "pages_ocr.json", list[Page],
                   lambda: ocr_pages(bid_pdf, pages, settings, safe_name(ctx.bidder)))
    stage("LABELLING")
    pages = cached(run_dir / "pages_labelled.json", list[Page],
                   lambda: label_pages(pages, criteria, llm))
    items = cached(run_dir / "items.json", list[Item], lambda: build_items(pages))
    by_no = {p.pdf_page_no: p for p in pages}
    results = _item_results(items, by_no, ctx, system_prompt(ctx, block), run_dir, llm, stage)
    stage("CHECKS", len(items), len(items))
    checks = cached(run_dir / "evidence_checks.json", list[EvidenceCheck],
                    lambda: [c for i in items if i.label in results
                             for c in check_item(results[i.label], i, by_no, settings)])
    copies = cached(run_dir / "copy_groups.json", list[CopyGroup],
                    lambda: check_copies(items, results))
    stage("SCORING", len(items), len(items))
    scores = [_score(c, items, results, checks, copies, by_no, ctx, run_dir, settings, llm)
              for c in criteria]
    write(run_dir / "scores.json", scores)
    return scores


def _run_meta(bid_pdf: Path, ctx: RunContext, criteria: list[Criterion], block: str,
              settings: Settings, run_id: str | None) -> dict:
    """Snapshot of everything the run depended on (audit + loading into the DB)."""
    return {"run_id": run_id or str(uuid.uuid4()), "context": ctx.model_dump(mode="json"),
            "bid_file": bid_pdf.name, "bid_sha256": sha256_file(bid_pdf),
            "model": settings.claude_model, "prompts": versions(),
            "criteria": [c.model_dump(mode="json") for c in criteria], "criteria_block": block}


def _item_results(items: list[Item], pages: dict[int, Page], ctx: RunContext, system: str,
                  run_dir: Path, llm: LlmClient, stage: Stage) -> dict[str, ItemResult]:
    results = {}
    for done, item in enumerate(items):
        stage("ITEMS", done, len(items))
        results[item.label] = cached(run_dir / "items" / f"{safe_name(item.label)}.json",
                                     ItemResult,
                                     lambda item=item: evaluate_item(item, pages, ctx, system, llm))
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
    return CriterionScore(code=criterion.code, llm_marks=result.marks,
                          checked_marks=arith.checked_marks, arithmetic_ok=arith.ok,
                          needs_review=bool(reasons), review_reasons=reasons,
                          summary="; ".join([result.summary, *arith.issues]))
