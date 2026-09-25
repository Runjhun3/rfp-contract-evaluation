"""Queries for evaluation runs, their progress and the job queue."""
import json

from app.db.connection import all_rows, one_row
from app.llm.prompts import versions


def start_run(cur, tender_id: str, prompt_id: str, model: str, user_id: str,
              submission_ids: list[str]) -> str:
    run = one_row(cur, """insert into evaluation_run (tender_id, prompt_id, prompt_versions, model,
                            status, triggered_by) values (%s, %s, %s::jsonb, %s, 'QUEUED', %s)
                          returning run_id::text""",
                  (tender_id, prompt_id, json.dumps(versions()), model, user_id))
    for submission_id in submission_ids:
        cur.execute("insert into run_submission (run_id, submission_id) values (%s, %s)",
                    (run["run_id"], submission_id))
        enqueue(cur, tender_id, "EVALUATE_SUBMISSION", submission_id, run["run_id"])
    cur.execute("update tender set status = 'EVALUATING' where tender_id = %s", (tender_id,))
    return run["run_id"]


def enqueue(cur, tender_id: str, kind: str, ref_id: str, run_id: str | None = None) -> None:
    cur.execute("""insert into job (tender_id, kind, ref_id, run_id) values (%s, %s, %s, %s)
                   on conflict (kind, ref_id, run_id) do nothing""",
                (tender_id, kind, ref_id, run_id))


def claim_job(cur) -> dict | None:
    return one_row(cur, """update job set status = 'RUNNING', attempts = attempts + 1,
                             updated_at = now()
                           where job_id = (select job_id from job
                                           where status = 'PENDING' and run_after <= now()
                                           order by job_id for update skip locked limit 1)
                           returning job_id, kind, ref_id::text, run_id::text, tender_id::text,
                                     attempts""")


def finish_job(cur, job_id: int, error: str | None, attempts: int, max_attempts: int = 3) -> None:
    if error is None:
        status, delay = "DONE", 0
    else:
        status, delay = ("PENDING", 60) if attempts < max_attempts else ("FAILED", 0)
    cur.execute("""update job set status = %s, last_error = %s, updated_at = now(),
                     run_after = now() + make_interval(secs => %s) where job_id = %s""",
                (status, (error or "")[:2000] or None, delay, job_id))


def set_stage(cur, run_id: str, submission_id: str, stage: str, done: int = 0,
              total: int = 0, error: str | None = None) -> None:
    cur.execute("""update run_submission set stage = %s, items_done = %s, items_total = %s,
                     error = %s where run_id = %s and submission_id = %s""",
                (stage, done, total, error, run_id, submission_id))
    cur.execute("""update evaluation_run set status = 'RUNNING', started_at = coalesce(started_at, now())
                   where run_id = %s and status = 'QUEUED'""", (run_id,))


def close_run_if_done(cur, run_id: str) -> None:
    cur.execute("""update evaluation_run r set status = case when exists (
                       select 1 from run_submission x where x.run_id = r.run_id and x.stage = 'FAILED')
                     then 'FAILED' else 'DONE' end, finished_at = now()
                   where r.run_id = %s and not exists (select 1 from run_submission x
                       where x.run_id = r.run_id and x.stage not in ('DONE', 'FAILED'))""", (run_id,))
    cur.execute("""update tender t set status = 'REVIEW' from evaluation_run r
                   where r.run_id = %s and r.tender_id = t.tender_id and r.status = 'DONE'""",
                (run_id,))


def get_run(cur, run_id: str) -> dict | None:
    return one_row(cur, """select run_id::text, tender_id::text, status, model,
                                  to_char(created_at, 'DD Mon YYYY HH24:MI') as started,
                                  (select version from evaluation_prompt p
                                    where p.prompt_id = r.prompt_id) as prompt_version
                           from evaluation_run r where run_id = %s""", (run_id,))


def latest_run(cur, tender_id: str) -> dict | None:
    return one_row(cur, """select run_id::text, status from evaluation_run where tender_id = %s
                           order by created_at desc limit 1""", (tender_id,))


def progress(cur, run_id: str) -> list[dict]:
    return all_rows(cur, """select x.submission_id::text, b.short_name, x.stage, x.items_done,
                                   x.items_total, x.error
                            from run_submission x join bid_submission s using (submission_id)
                            join bidder b using (bidder_id)
                            where x.run_id = %s order by b.short_name""", (run_id,))
