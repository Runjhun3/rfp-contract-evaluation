"""Queries for audit_event (migration 017): participants, firms, and the history the
export's audit log shows with the jobs that ran. Append-only."""
import json

from app.db.connection import all_rows


def add(cur, tender_id: str | None, actor: str | None, action: str, target: str,
        details: dict) -> None:
    """tender_id None: the shared firm list. details should hold the firm's bidder_id,
    so a project's history can find events about its firms."""
    cur.execute("""insert into audit_event (tender_id, actor, action, target, details)
                   values (%s, %s, %s, %s, %s::jsonb)""",
                (tender_id, actor, action, target, json.dumps(details)))


def project_history(cur, tender_id: str) -> list[dict]:
    """Newest first, in the shape of q_audit.criteria_history: the project's participant
    events, firm-list events about its firms, and every job with why and who queued it.
    code: the firm (or "RFP"); old: the details; new: a changed value."""
    return all_rows(cur, """
        select to_char(at, 'DD Mon YYYY HH24:MI') as stamp, who, what, code, old, new
        from (
          select e.at, e.event_id as seq, u.full_name as who, e.action as what,
                 e.target as code,
                 e.details->>'note' as old, e.details->>'new' as new
          from audit_event e left join app_user u on u.user_id = e.actor
          where e.tender_id = %s
             or (e.tender_id is null and e.details->>'bidder_id' in (
                   select bidder_id::text from bid_submission where tender_id = %s))
          union all
          select j.created_at, j.job_id, u.full_name,
                 initcap(replace(j.kind, '_', ' ')) || ' · ' || lower(j.status),
                 coalesce(b.short_name, case when j.kind = 'EXTRACT_CRITERIA' then 'RFP' end),
                 nullif(concat_ws(' · ', nullif(j.cause, ''), j.last_error), ''), null
          from job j left join app_user u on u.user_id = j.created_by
          left join bid_submission s on s.submission_id = j.ref_id
                                     and j.kind <> 'EXTRACT_CRITERIA'
          left join bidder b on b.bidder_id = s.bidder_id
          where j.tender_id = %s) h
        order by at desc, seq desc""", (tender_id, tender_id, tender_id))
