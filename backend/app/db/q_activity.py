"""The activity log (docs/decisions.md D-059): every action a person took, read back from
the tables that already record it, newest first. What the AI or the worker did on its
own (extractions, job outcomes) has no account and is left out. Read-only.

Each row: stamp, who, category, what, project (none for accounts and sign-ins), details.
Filters: the categories, and optionally who (an account's user_id), since and until
(dates, both included; IST like every timestamp here).
"""
from app.db.connection import all_rows, one_row
from app.db.q_events import ACCOUNT_ACTIONS

PAGE_SIZE = 50
CSV_MAX = 50000                       # rows in one downloaded file
CATEGORIES = {"PROJECT": "Projects & RFP", "CRITERIA": "Criteria & rule text",
              "PARTICIPANTS": "Participants & bids", "EVALUATION": "Evaluation",
              "DECISIONS": "Committee decisions", "EXPORTS": "Exports",
              "ACCOUNTS": "Accounts", "SIGN_IN": "Sign-in"}
SIGN_IN_ACTIONS = ["Signed in", "Signed out"]
SHEET_EXPORTED = "Evaluation sheet exported"
LOG_DOWNLOADED = "Activity log downloaded"

_ACTIONS = """
  select t.created_at as at, t.created_by as actor, t.tender_id, 'PROJECT' as category,
         'Project created' as what, t.name as details, null as bidder from tender t
  union all
  select t.deleted_at, t.deleted_by, t.tender_id, 'PROJECT', 'Project deleted', t.name, null
  from tender t where t.deleted_at is not null
  union all
  select d.uploaded_at, d.uploaded_by, d.tender_id, 'PROJECT', 'RFP uploaded', d.file_name,
         null
  from tender_document d
  union all
  select e.edited_at, e.edited_by, e.tender_id, 'CRITERIA', 'Criterion edited',
         e.code || ' · ' || e.field || ': ' || coalesce(e.old_value, '—') || ' → '
           || coalesce(e.new_value, '—'), null
  from criterion_edit e
  union all
  select s.saved_at, s.saved_by, p.tender_id, 'CRITERIA', 'Rule text saved',
         'version ' || p.version, null
  from prompt_draft_save s join evaluation_prompt p using (prompt_id)
  union all
  select p.approved_at, p.approved_by, p.tender_id, 'CRITERIA', 'Criteria approved',
         'rule text version ' || p.version, null
  from evaluation_prompt p where p.status = 'APPROVED'
  union all
  select f.uploaded_at, f.uploaded_by, s.tender_id, 'PARTICIPANTS', 'Bid uploaded',
         b.short_name || ': ' || f.file_name, null
  from submission_file f join bid_submission s using (submission_id) join bidder b using (bidder_id)
  union all
  select e.at, e.actor, e.tender_id,
         case when e.action = any(%(accounts)s) then 'ACCOUNTS'
              when e.action = any(%(sign_in)s) then 'SIGN_IN'
              when e.action = any(%(exports)s) then 'EXPORTS' else 'PARTICIPANTS' end,
         e.action, concat_ws(' · ', nullif(e.target, ''), e.details->>'note', e.details->>'new'),
         e.details->>'bidder_id'
  from audit_event e
  union all
  select r.created_at, r.triggered_by, r.tender_id, 'EVALUATION', 'Evaluation started',
         (select string_agg(b.short_name, ', ' order by b.short_name) from run_submission x
          join bid_submission s using (submission_id) join bidder b using (bidder_id)
          where x.run_id = r.run_id), null
  from evaluation_run r
  union all
  select j.created_at, j.created_by, j.tender_id, 'EVALUATION', 'Eligibility checked again',
         b.short_name, null
  from job j join bid_submission s on s.submission_id = j.ref_id
  join bidder b using (bidder_id) where j.cause = 'Check eligibility again'
  union all
  select d.decided_at, d.reviewer, c.tender_id, 'DECISIONS',
         case d.action when 'OVERRIDE' then 'Marks overridden' else 'Marks accepted' end,
         concat_ws(' · ', b.short_name, c.code, coalesce(nullif(i.title, ''), i.label))
           || ': ' || trim_scale(d.final_marks), null
  from review_decision d join criterion_score s using (score_id)
  join criterion c on c.criterion_id = s.criterion_id
  join bid_submission bs on bs.submission_id = s.submission_id
  join bidder b on b.bidder_id = bs.bidder_id
  left join bid_item i on i.item_id = d.item_id
  union all
  select x.decided_at, x.reviewer, e.tender_id, 'DECISIONS', 'Eligibility decided',
         b.short_name || ' · ' || coalesce(c.rfp_no, c.code) || ': '
           || case x.decision when 'MET' then 'met' else 'not met' end, null
  from eligibility_decision x join eligibility_check e using (check_id)
  join criterion c on c.criterion_id = e.criterion_id
  join bid_submission bs on bs.submission_id = e.submission_id
  join bidder b on b.bidder_id = bs.bidder_id
  union all
  select h.entered_at, h.entered_by, c.tender_id, 'DECISIONS', 'Committee marks entered',
         b.short_name || ' · ' || c.code || ': ' || trim_scale(h.marks), null
  from manual_score_history h join criterion c using (criterion_id)
  join bid_submission bs using (submission_id) join bidder b using (bidder_id)"""


_FILTERED = f"""
        from ({_ACTIONS}) a
        join app_user u on u.user_id = a.actor          -- a person acted: never the AI
        left join tender t on t.tender_id = a.tender_id
        where (%(tender)s::uuid is null or a.tender_id = %(tender)s::uuid
               -- the shared firm list: events about this project's firms
               or (a.tender_id is null and a.bidder in (
                   select bidder_id::text from bid_submission where tender_id = %(tender)s::uuid)))
          and a.category = any(%(categories)s)
          and (%(who)s::uuid is null or a.actor = %(who)s::uuid)
          and (%(since)s::date is null or a.at >= %(since)s::date)
          and (%(until)s::date is null or a.at < %(until)s::date + 1)"""


def _params(tender_id: str | None, filters: dict, **more) -> dict:
    return {"accounts": list(ACCOUNT_ACTIONS), "sign_in": SIGN_IN_ACTIONS,
            "exports": [SHEET_EXPORTED, LOG_DOWNLOADED], "tender": tender_id,
            "categories": filters["categories"], "who": filters.get("who"),
            "since": filters.get("since"), "until": filters.get("until"), **more}


def count(cur, tender_id: str | None, filters: dict) -> int:
    """How many actions match: of one project, or of every project and account."""
    return one_row(cur, f"select count(*) as n {_FILTERED}", _params(tender_id, filters))["n"]


def actions(cur, tender_id: str | None, filters: dict, page: int | None) -> list[dict]:
    """The matching actions, newest first: one page, or (page None) all of them for a
    downloaded file, up to CSV_MAX."""
    limit, offset = (CSV_MAX, 0) if page is None else (PAGE_SIZE, (page - 1) * PAGE_SIZE)
    return all_rows(cur, f"""
        select to_char(a.at, 'DD Mon YYYY, HH24:MI:SS') as stamp, u.full_name as who,
               a.category, a.what, t.name as project, a.details
        {_FILTERED}
        order by a.at desc limit %(limit)s offset %(offset)s""",
                    _params(tender_id, filters, limit=limit, offset=offset))


def people(cur) -> list[dict]:
    """Every account, for the "who" filter."""
    return all_rows(cur, """select user_id::text, full_name as name from app_user
                            order by lower(full_name)""")
