"""What the worker does for each job kind."""
import json
from pathlib import Path

from pydantic import ValidationError

from app import files
from app.config import Settings
from app.criteria import SCREENED
from app.db import q_projects, q_runs
from app.db.connection import one_row, transaction
from app.db.save_run import save_output
from app.ingest.extract_criteria import build_block, decimal_or_none, extract
from app.ingest.ocr import ocr_pages
from app.ingest.read_pages import read_pages
from app.jobs import tender_rules
from app.llm.client import LlmClient
from app.pipeline import run as run_pipeline
from app.schemas.records import CountBand, RunContext


def extract_criteria(settings: Settings, llm: LlmClient, job: dict) -> None:
    with transaction(settings) as cur:
        doc = one_row(cur, "select tender_id::text, s3_key from tender_document where doc_id = %s",
                      (job["ref_id"],))
    pdf = files.local_path(settings, doc["s3_key"])
    pages = ocr_pages(pdf, read_pages(pdf), settings, f"rfp-{job['ref_id']}")
    found = extract(pages, llm)
    with transaction(settings) as cur:
        for c in found.criteria:
            _upsert_criterion(cur, doc["tender_id"], c)
        q_projects.drop_stale_criteria(cur, doc["tender_id"], [c.code for c in found.criteria])
        q_projects.save_draft_block(cur, doc["tender_id"],
                                    build_block(q_projects.criteria(cur, doc["tender_id"]),
                                                found.general_conditions))
        q_projects.set_status(cur, doc["tender_id"], "CRITERIA_READY")


def _upsert_criterion(cur, tender_id: str, c) -> None:
    stage = c.stage if c.stage in (*SCREENED, "TECHNICAL", "PRESENTATION") else "TECHNICAL"
    cur.execute("""insert into criterion (tender_id, code, parent_code, stage, kind, title, rfp_text,
                     meaning, max_marks, max_items, allowed_item_marks, scored_by, rfp_page,
                     count_bands, proof, rfp_no, source_reference, considered, classification_unsure)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::numeric[], %s, %s,
                           %s::jsonb, %s, %s, %s, %s, %s)
                   on conflict (tender_id, code) do update set parent_code = excluded.parent_code,
                     stage = excluded.stage,
                     kind = excluded.kind, title = excluded.title, rfp_text = excluded.rfp_text,
                     meaning = excluded.meaning, max_marks = excluded.max_marks,
                     max_items = excluded.max_items, allowed_item_marks = excluded.allowed_item_marks,
                     scored_by = excluded.scored_by, rfp_page = excluded.rfp_page,
                     count_bands = excluded.count_bands, proof = excluded.proof,
                     rfp_no = excluded.rfp_no, source_reference = excluded.source_reference,
                     considered = excluded.considered,
                     classification_unsure = excluded.classification_unsure""",
                (tender_id, c.code, c.parent, stage, c.kind if c.kind in ("PROJECT", "CV") else None,
                 c.title, c.rfp_text, c.meaning, decimal_or_none(c.max_marks), c.max_items,
                 [m for m in c.item_marks if decimal_or_none(m) is not None],
                 # A presentation is always the committee's to mark, whatever scored_by says.
                 "COMMITTEE" if c.scored_by == "COMMITTEE" or stage == "PRESENTATION"
                 else "LLM", c.rfp_page,
                 json.dumps(_bands(c.count_bands)),
                 c.proof if stage in SCREENED else None,
                 ((c.rfp_no or "").strip().rstrip(".") or None) if stage in SCREENED else None,
                 c.source_reference,
                 not c.classification_unsure, c.classification_unsure))


def _bands(raw: list[dict]) -> list[dict]:
    """Count bands as extracted, kept only when every band is well formed."""
    try:
        bands = [CountBand.model_validate(b) for b in raw]
    except ValidationError:
        return []
    return [{"min": b.min, "max": b.max, "marks": str(b.marks)} for b in bands]


def evaluate_submission(settings: Settings, llm: LlmClient, job: dict) -> None:
    run_id, submission_id = job["run_id"], job["ref_id"]
    with transaction(settings) as cur:
        ctx, block, criteria, ids, file, requirements = _load(cur, run_id, submission_id)
    stage = _stage_writer(settings, run_id, submission_id)
    run_pipeline(files.local_path(settings, file["s3_key"]), ctx, criteria, block,
                 Path(settings.runs_dir) / run_id / submission_id, settings, llm,
                 run_id=run_id, on_stage=stage, requirements=requirements)
    with transaction(settings) as cur:
        save_output(cur, Path(settings.runs_dir) / run_id / submission_id, run_id,
                    submission_id, file["file_id"], ids)
        q_runs.set_stage(cur, run_id, submission_id, "DONE")
        q_runs.close_run_if_done(cur, run_id)


def _stage_writer(settings: Settings, run_id: str, submission_id: str):
    def write(name: str, done: int = 0, total: int = 0) -> None:
        with transaction(settings) as cur:
            q_runs.set_stage(cur, run_id, submission_id, name, done, total)
    return write


def _load(cur, run_id: str, submission_id: str):
    head = one_row(cur, """
        select t.name, t.gem_bid_no, coalesce(t.department, '') as department,
               t.bid_due_date::text as due, p.criteria_block, b.short_name, t.tender_id::text
        from evaluation_run r join tender t using (tender_id)
        join evaluation_prompt p on p.prompt_id = r.prompt_id
        join bid_submission s on s.submission_id = %s join bidder b using (bidder_id)
        where r.run_id = %s""", (submission_id, run_id))
    every = q_projects.criterion_rows(cur, head["tender_id"])
    criteria, ids = tender_rules.scored(every)
    file = one_row(cur, """select file_id::text, s3_key from submission_file where submission_id = %s
                           order by uploaded_at desc limit 1""", (submission_id,))
    ctx = RunContext(tender_no=head["gem_bid_no"] or head["name"], department=head["department"],
                     bidder=head["short_name"], bid_due_date=head["due"])
    return (ctx, head["criteria_block"], criteria, ids, file,
            tender_rules.requirements(every))
