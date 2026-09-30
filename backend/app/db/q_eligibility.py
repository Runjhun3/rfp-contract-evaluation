"""Queries for eligibility screening: the AI's checks, the committee's decisions, and
the CHECK_ELIGIBILITY jobs. Checks and decisions are append-only."""
import json

from app.db.connection import all_rows, one_row

JOB = "CHECK_ELIGIBILITY"


def current(cur, tender_id: str, submission_id: str | None = None) -> list[dict]:
    """The latest check of each (submission, requirement) with its latest decision, for
    the tender or one of its submissions."""
    return all_rows(cur, """
    select distinct on (e.submission_id, e.criterion_id)
           e.check_id::text, e.submission_id::text, e.criterion_id::text, c.code, c.title,
           c.stage,
           e.file_id::text, e.result, e.finding, e.facts, e.verification, e.pages,
           to_char(e.checked_at, 'DD Mon YYYY HH24:MI') as checked,
           d.decision, d.reason as decision_reason, d.full_name as decided_by,
           to_char(d.decided_at, 'DD Mon YYYY HH24:MI') as decided
    from eligibility_check e join criterion c on c.criterion_id = e.criterion_id
    left join lateral (select x.decision, x.reason, x.decided_at, u.full_name
                       from eligibility_decision x join app_user u on u.user_id = x.reviewer
                       where x.check_id = e.check_id
                       order by x.decided_at desc limit 1) d on true
    where c.stage in ('ELIGIBILITY', 'DOCUMENT') and e.tender_id = %s
      and (%s::uuid is null or e.submission_id = %s::uuid)
    order by e.submission_id, e.criterion_id, e.checked_at desc""",
                    (tender_id, submission_id, submission_id))


def save_check(cur, tender_id: str, submission_id: str, file_id: str, check: dict,
               prompt_version: str, model: str) -> None:
    cur.execute("""insert into eligibility_check (tender_id, submission_id, criterion_id, file_id,
                     result, finding, facts, verification, pages, prompt_version, model)
                   values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)""",
                (tender_id, submission_id, check["criterion_id"], file_id, check["result"],
                 check["finding"], json.dumps(check["facts"]), json.dumps(check["verification"]),
                 check["pages"], prompt_version, model))


def screened_bids(cur, tender_id: str) -> list[dict]:
    """The bids screening shows: every ticked participant with a bid file, and every
    unticked one that was already checked (its results stay, as on the results page)."""
    return all_rows(cur, """
        select s.submission_id::text, b.short_name, b.legal_name, s.included,
               f.file_id::text
        from bid_submission s join bidder b using (bidder_id)
        join lateral (select file_id from submission_file x
                      where x.submission_id = s.submission_id
                      order by x.uploaded_at desc limit 1) f on true
        where s.tender_id = %s
          and (s.included or exists (select 1 from eligibility_check e
                                     where e.submission_id = s.submission_id))
        order by b.short_name""", (tender_id,))


def subject(cur, submission_id: str) -> dict | None:
    """The bid a CHECK_ELIGIBILITY job checks: its tender, firm and latest bid file."""
    return one_row(cur, """
        select s.tender_id::text, t.name, t.gem_bid_no, coalesce(t.department, '') as department,
               t.bid_due_date::text as due, b.short_name, f.file_id::text, f.s3_key
        from bid_submission s join tender t using (tender_id) join bidder b using (bidder_id)
        join lateral (select file_id, s3_key from submission_file x
                      where x.submission_id = s.submission_id
                      order by x.uploaded_at desc limit 1) f on true
        where s.submission_id = %s""", (submission_id,))


def get_check(cur, check_id: str) -> dict | None:
    return one_row(cur, """select e.check_id::text, e.tender_id::text, e.submission_id::text,
                                  e.criterion_id::text, e.result, b.short_name
                           from eligibility_check e
                           join bid_submission s on s.submission_id = e.submission_id
                           join bidder b on b.bidder_id = s.bidder_id
                           where e.check_id = %s""", (check_id,))


def record_decision(cur, check_id: str, decision: str, reason: str, user_id: str) -> None:
    cur.execute("""insert into eligibility_decision (check_id, decision, reason, reviewer)
                   values (%s, %s, %s, %s)""", (check_id, decision, reason, user_id))


def decisions(cur, tender_id: str) -> list[dict]:
    """Every decision on the tender's checks, oldest first (the exported log)."""
    return all_rows(cur, """
        select e.submission_id::text, c.code, c.rfp_no, c.stage, x.decision, x.reason,
               u.full_name,
               to_char(x.decided_at, 'DD Mon YYYY HH24:MI') as decided
        from eligibility_decision x join eligibility_check e using (check_id)
        join criterion c on c.criterion_id = e.criterion_id
        join app_user u on u.user_id = x.reviewer
        where e.tender_id = %s order by x.decided_at""", (tender_id,))


def jobs(cur, tender_id: str) -> dict[str, dict]:
    """Each submission's latest eligibility job: {submission_id: {status, error}}."""
    rows = all_rows(cur, """select distinct on (ref_id) ref_id::text, status, last_error
                            from job where tender_id = %s and kind = %s
                            order by ref_id, created_at desc""", (tender_id, JOB))
    return {r["ref_id"]: {"status": r["status"], "error": r["last_error"]} for r in rows}


def enqueue_check(cur, tender_id: str, submission_id: str) -> None:
    """Queue a check of the submission's latest bid file, unless one is already queued."""
    cur.execute("""insert into job (tender_id, kind, ref_id)
                   select %s, %s, %s where not exists (
                     select 1 from job where kind = %s and ref_id = %s
                       and status = 'PENDING')""",
                (tender_id, JOB, submission_id, JOB, submission_id))
