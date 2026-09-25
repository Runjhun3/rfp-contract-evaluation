"""Find-or-create the rows a run hangs off: user, tender, criteria, prompt, bidder,
submission, file. Every function is idempotent (safe to call twice).
"""
import json

from app.schemas.records import Criterion, RunContext


def ensure_user(cur, email: str, full_name: str, role: str = "EVALUATOR") -> str:
    cur.execute("""insert into app_user (email, full_name, role) values (%s, %s, %s)
                   on conflict (email) do update set email = excluded.email
                   returning user_id""", (email, full_name, role))
    return str(cur.fetchone()[0])


def ensure_tender(cur, ctx: RunContext, name: str, user_id: str) -> str:
    cur.execute("""insert into tender (name, gem_bid_no, department, bid_due_date, status, created_by)
                   values (%s, %s, %s, %s, 'PROMPT_APPROVED', %s)
                   on conflict (gem_bid_no) do update set bid_due_date = excluded.bid_due_date
                   returning tender_id""",
                (name, ctx.tender_no, ctx.department, ctx.bid_due_date.isoformat(), user_id))
    return str(cur.fetchone()[0])


def ensure_criteria(cur, tender_id: str, criteria: list[Criterion]) -> dict[str, str]:
    ids = {}
    for c in criteria:
        cur.execute("""insert into criterion (tender_id, code, parent_code, stage, kind, title,
                         rfp_text, meaning, max_marks, max_items, allowed_item_marks, scored_by)
                       values (%s, %s, %s, 'TECHNICAL', %s, %s, %s, %s, %s, %s, %s::numeric[], 'LLM')
                       on conflict (tender_id, code) do update set meaning = excluded.meaning
                       returning criterion_id""",
                    (tender_id, c.code, c.code.split(".")[0], c.kind, c.title,
                     c.rfp_text or c.meaning, c.meaning, c.max_marks, c.max_items,
                     [str(m) for m in c.allowed_item_marks]))
        ids[c.code] = str(cur.fetchone()[0])
    return ids


def ensure_prompt(cur, tender_id: str, block: str, user_id: str) -> str:
    cur.execute("""select prompt_id from evaluation_prompt
                   where tender_id = %s and criteria_block = %s""", (tender_id, block))
    row = cur.fetchone()
    if row:
        return str(row[0])
    cur.execute("""insert into evaluation_prompt (tender_id, version, criteria_block, status,
                     approved_by, approved_at)
                   select %s, coalesce(max(version), 0) + 1, %s, 'APPROVED', %s, now()
                   from evaluation_prompt where tender_id = %s
                   returning prompt_id""", (tender_id, block, user_id, tender_id))
    return str(cur.fetchone()[0])


def ensure_submission(cur, tender_id: str, bidder: str) -> str:
    cur.execute("""insert into bidder (legal_name, short_name) values (%s, %s)
                   on conflict (legal_name) do update set short_name = excluded.short_name
                   returning bidder_id""", (bidder, bidder))
    bidder_id = str(cur.fetchone()[0])
    cur.execute("""insert into bid_submission (tender_id, bidder_id, status)
                   values (%s, %s, 'INGESTED')
                   on conflict (tender_id, bidder_id) do update set status = 'INGESTED'
                   returning submission_id""", (tender_id, bidder_id))
    return str(cur.fetchone()[0])


def ensure_file(cur, submission_id: str, meta: dict, page_count: int, user_id: str) -> str:
    cur.execute("""insert into submission_file (submission_id, file_name, s3_key, sha256,
                     page_count, pages_done, uploaded_by)
                   values (%s, %s, %s, %s, %s, %s, %s)
                   on conflict (submission_id, sha256) do update set pages_done = excluded.pages_done
                   returning file_id""",
                (submission_id, meta["bid_file"], f"local/{meta['bid_file']}",
                 meta["bid_sha256"], page_count, page_count, user_id))
    return str(cur.fetchone()[0])


def insert_run(cur, meta: dict, tender_id: str, prompt_id: str, user_id: str,
               submission_id: str, items_total: int) -> None:
    cur.execute("""insert into evaluation_run (run_id, tender_id, prompt_id, prompt_versions, model,
                     status, triggered_by, started_at, finished_at)
                   values (%s, %s, %s, %s::jsonb, %s, 'DONE', %s, now(), now())""",
                (meta["run_id"], tender_id, prompt_id, json.dumps(meta["prompts"]),
                 meta["model"], user_id))
    cur.execute("""insert into run_submission (run_id, submission_id, stage, items_total, items_done)
                   values (%s, %s, 'DONE', %s, %s)""",
                (meta["run_id"], submission_id, items_total, items_total))
