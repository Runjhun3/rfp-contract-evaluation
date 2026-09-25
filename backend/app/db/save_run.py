"""Load a finished run folder into Postgres, in one transaction.

Idempotent: a run whose run_id is already in the database is skipped.
Used by `python run.py save-run` now; the worker will call the same functions
directly once the API exists.
"""
from pathlib import Path

from app.config import Settings
from app.db import repo_setup as setup
from app.db.connection import transaction
from app.db.save_results import save_results
from app.schemas.records import Criterion, Item, Page, RunContext
from app.storage import read


def save_run(settings: Settings, run_dir: Path, tender_name: str, user_email: str) -> str:
    meta = read(run_dir / "run.json")
    ctx = RunContext.model_validate(meta["context"])
    pages = read(run_dir / "pages_labelled.json")
    items = read(run_dir / "items.json")
    with transaction(settings) as cur:
        cur.execute("select 1 from evaluation_run where run_id = %s", (meta["run_id"],))
        if cur.fetchone():
            return meta["run_id"]
        user_id = setup.ensure_user(cur, user_email, user_email.split("@")[0])
        tender_id = setup.ensure_tender(cur, ctx, tender_name, user_id)
        criteria = [Criterion.model_validate(c) for c in meta["criteria"]]
        criterion_ids = setup.ensure_criteria(cur, tender_id, criteria)
        prompt_id = setup.ensure_prompt(cur, tender_id, meta["criteria_block"], user_id)
        submission_id = setup.ensure_submission(cur, tender_id, ctx.bidder)
        file_id = setup.ensure_file(cur, submission_id, meta, len(pages), user_id)
        setup.insert_run(cur, meta, tender_id, prompt_id, user_id, submission_id, len(items))
        save_output(cur, run_dir, meta["run_id"], submission_id, file_id, criterion_ids)
        cur.execute("update tender set status = 'REVIEW' where tender_id = %s", (tender_id,))
    return meta["run_id"]


def save_output(cur, run_dir: Path, run_id: str, submission_id: str, file_id: str,
                criterion_ids: dict[str, str]) -> None:
    """Pages, labels, items, judgements, checks and scores of one bidder in one run."""
    pages = [Page.model_validate(p) for p in read(run_dir / "pages_labelled.json")]
    items = [Item.model_validate(i) for i in read(run_dir / "items.json")]
    page_ids = _save_pages(cur, file_id, pages)
    _save_labels(cur, run_id, page_ids, pages)
    save_results(cur, run_dir, run_id, submission_id, criterion_ids, items)


def _clean(text: str | None) -> str | None:
    return text.replace("\x00", "") if text else text   # Postgres text can't hold NUL


def _save_pages(cur, file_id: str, pages: list[Page]) -> dict[int, int]:
    cur.executemany(
        """insert into page (file_id, pdf_page_no, text, image_ratio, ocr_text, extraction,
             ocr_confidence) values (%s, %s, %s, %s, %s, %s, %s)
           on conflict (file_id, pdf_page_no) do nothing""",
        [(file_id, p.pdf_page_no, _clean(p.text), p.image_ratio, _clean(p.ocr_text),
          p.extraction, p.ocr_confidence) for p in pages])
    cur.execute("select pdf_page_no, page_id from page where file_id = %s", (file_id,))
    return {int(no): int(pid) for no, pid in cur.fetchall()}


def _save_labels(cur, run_id: str, page_ids: dict[int, int], pages: list[Page]) -> None:
    cur.executemany(
        """insert into page_label (run_id, page_id, page_type, criterion_code, map_confidence,
             item_start) values (%s, %s, %s, %s, %s, %s)""",
        [(run_id, page_ids[p.pdf_page_no], p.page_type or "OTHER", p.criterion_code,
          p.map_confidence, p.item_start) for p in pages if p.pdf_page_no in page_ids])
