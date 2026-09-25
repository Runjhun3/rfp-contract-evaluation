"""Background worker: takes one job at a time from the `job` table
(FOR UPDATE SKIP LOCKED), so several workers can run side by side.
"""
import logging
import time

from app.config import Settings
from app.db import q_runs
from app.db.connection import transaction
from app.jobs import handlers
from app.llm.client import LlmClient

log = logging.getLogger("worker")
HANDLERS = {"EXTRACT_CRITERIA": handlers.extract_criteria,
            "EVALUATE_SUBMISSION": handlers.evaluate_submission}
MAX_ATTEMPTS = 3
IDLE_SECONDS = 3


def run_once(settings: Settings, llm: LlmClient) -> bool:
    """Process one job. Returns False when the queue is empty."""
    with transaction(settings) as cur:
        job = q_runs.claim_job(cur)
    if job is None:
        return False
    error = None
    try:
        HANDLERS[job["kind"]](settings, llm, job)
    except Exception as err:          # recorded on the job; the worker keeps running
        error = f"{type(err).__name__}: {err}"
        log.exception("job %s failed", job["job_id"])
        _mark_failed_stage(settings, job, error)
    with transaction(settings) as cur:
        q_runs.finish_job(cur, job["job_id"], error, job["attempts"], MAX_ATTEMPTS)
    return True


def _mark_failed_stage(settings: Settings, job: dict, error: str) -> None:
    if job["kind"] != "EVALUATE_SUBMISSION":
        return
    final = job["attempts"] >= MAX_ATTEMPTS
    with transaction(settings) as cur:
        q_runs.set_stage(cur, job["run_id"], job["ref_id"], "FAILED" if final else "QUEUED",
                         error=error[:500])
        if final:
            q_runs.close_run_if_done(cur, job["run_id"])


def forever(settings: Settings) -> None:
    llm = LlmClient(settings)
    log.info("worker started")
    while True:
        if not run_once(settings, llm):
            time.sleep(IDLE_SECONDS)
