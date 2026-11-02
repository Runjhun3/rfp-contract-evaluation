"""Queries for the audit trail (migration 016): criteria edits, extraction snapshots,
and the history read back for the results page and the export's audit log.
Every table written here is append-only."""
import json

from app.db.connection import all_rows, one_row


def add_edit(cur, tender_id: str, row: dict, field: str, values: tuple, source: str,
             user_id: str | None) -> None:
    """values: (old, new) as the trail shows them."""
    cur.execute("""insert into criterion_edit (tender_id, criterion_id, code, field, old_value,
                     new_value, source, edited_by)
                   values (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (tender_id, row["criterion_id"], row["code"], field, *values, source, user_id))


def save_extraction(cur, tender_id: str, doc_id: str, versions: tuple[str, str],
                    found: dict) -> None:
    """versions: (prompt version, model). found: what the AI returned, as JSON."""
    cur.execute("""insert into criteria_extraction (tender_id, doc_id, prompt_version, model,
                     criteria, general)
                   values (%s, %s, %s, %s, %s::jsonb, %s::jsonb)""",
                (tender_id, doc_id, *versions, json.dumps(found["criteria"]),
                 json.dumps(found["general_conditions"])))


def latest_general(cur, tender_id: str) -> list[dict] | None:
    """The RFP's general conditions from the latest extraction, as the AI returned them;
    None when no extraction was recorded (projects read before migration 016)."""
    row = one_row(cur, """select general from criteria_extraction where tender_id = %s
                          order by extracted_at desc, extraction_id desc limit 1""",
                  (tender_id,))
    return row["general"] if row else None


def criteria_history(cur, tender_id: str) -> list[dict]:
    """The setup trail, newest first: extractions, criteria edits, rule text saves and
    approvals. Each: stamp, who (None: the AI), what, code, old, new."""
    return all_rows(cur, """
        select to_char(at, 'DD Mon YYYY, HH24:MI:SS') as stamp, who, what, code, old, new
        from (
          select x.extracted_at as at, null as who, 'Criteria extracted' as what,
                 null as code, d.file_name || ' · ' || x.prompt_version || ' · ' || x.model
                   as old, null as new
          from criteria_extraction x join tender_document d using (doc_id)
          where x.tender_id = %s
          union all
          select e.edited_at, u.full_name, 'Edited: ' || e.field, e.code, e.old_value,
                 e.new_value
          from criterion_edit e left join app_user u on u.user_id = e.edited_by
          where e.tender_id = %s
          union all
          select s.saved_at, u.full_name, 'Rule text saved', 'version ' || p.version, null,
                 null
          from prompt_draft_save s join evaluation_prompt p using (prompt_id)
          left join app_user u on u.user_id = s.saved_by
          where p.tender_id = %s
          union all
          select p.approved_at, u.full_name, 'Rule text approved', 'version ' || p.version,
                 null, null
          from evaluation_prompt p join app_user u on u.user_id = p.approved_by
          where p.tender_id = %s and p.status = 'APPROVED') h
        order by at desc""", (tender_id, tender_id, tender_id, tender_id))


def mark_history(cur, tender_id: str) -> list[dict]:
    """Every committee mark entered on the tender, oldest first."""
    return all_rows(cur, """
        select h.submission_id::text, h.criterion_id::text, c.code, b.short_name,
               trim_scale(h.marks) as marks, h.reason, u.full_name,
               to_char(h.entered_at, 'DD Mon YYYY HH24:MI') as stamp
        from manual_score_history h join criterion c using (criterion_id)
        join bid_submission s using (submission_id) join bidder b using (bidder_id)
        join app_user u on u.user_id = h.entered_by
        where c.tender_id = %s
        order by h.entered_at, h.history_id""", (tender_id,))



def committee_decisions(cur, tender_id: str) -> list[dict]:
    """Every decision the committee took on the project, newest first: on an item's or a
    criterion's marks (review_decision), committee-entered marks (manual_score_history)
    and eligibility checks. kind: ACCEPT / OVERRIDE (marks), MARKS (entered), MET /
    NOT_MET (eligibility); ai: what the AI said, for comparison."""
    return all_rows(cur, """
        select firm, to_char(at, 'DD Mon YYYY, HH24:MI:SS') as stamp, who, area, criterion,
               kind, value, ai, reason, code, code_label
        from (
          select b.short_name as firm, d.decided_at as at, u.full_name as who,
                 'Marks' as area,
                 concat_ws(' · ', c.code, coalesce(nullif(i.title, ''), i.label)) as criterion,
                 d.action as kind, trim_scale(d.final_marks)::text as value,
                 trim_scale(case when i.item_id is null then s.checked_marks
                                 when r.counted then r.marks else 0 end)::text as ai,
                 nullif(d.reason, '') as reason, c.code, c.code as code_label
          from review_decision d join criterion_score s using (score_id)
          join criterion c on c.criterion_id = s.criterion_id
          join bid_submission bs on bs.submission_id = s.submission_id
          join bidder b on b.bidder_id = bs.bidder_id
          join app_user u on u.user_id = d.reviewer
          left join bid_item i on i.item_id = d.item_id
          left join item_result r on r.item_id = d.item_id
          where c.tender_id = %s
          union all
          select b.short_name, h.entered_at, u.full_name, 'Committee marks', c.code, 'MARKS',
                 trim_scale(h.marks)::text, null, nullif(h.reason, ''), c.code, c.code
          from manual_score_history h join criterion c using (criterion_id)
          join bid_submission bs using (submission_id) join bidder b using (bidder_id)
          join app_user u on u.user_id = h.entered_by
          where c.tender_id = %s
          union all
          select b.short_name, x.decided_at, u.full_name, 'Eligibility',
                 coalesce(c.rfp_no, c.code) || ' · ' || c.title, x.decision, null, e.result,
                 nullif(x.reason, ''), c.code, 'Eligibility ' || coalesce(c.rfp_no, c.code)
          from eligibility_decision x join eligibility_check e using (check_id)
          join criterion c on c.criterion_id = e.criterion_id
          join bid_submission bs on bs.submission_id = e.submission_id
          join bidder b on b.bidder_id = bs.bidder_id
          join app_user u on u.user_id = x.reviewer
          where e.tender_id = %s) h
        order by firm, at desc""", (tender_id, tender_id, tender_id))
