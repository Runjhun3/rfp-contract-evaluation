"""Queries for the results matrix, evidence review and committee decisions."""
from app.db.connection import all_rows, one_row


def latest_attempts(cur, tender_id: str) -> list[dict]:
    """Every participant that is ticked or has been evaluated, with its most recent
    evaluation (run and stage); stage NOT_STARTED when it was never evaluated. A firm
    unticked only to leave it out of a later run keeps its results."""
    return all_rows(cur, """
        select s.submission_id::text, b.short_name, b.legal_name, s.included, x.run_id::text,
               coalesce(x.stage, 'NOT_STARTED') as stage
        from bid_submission s join bidder b using (bidder_id)
        left join lateral (select rs.run_id, rs.stage from run_submission rs
                           join evaluation_run r using (run_id)
                           where rs.submission_id = s.submission_id
                           order by r.created_at desc limit 1) x on true
        where s.tender_id = %s and (s.included or x.run_id is not null)
        order by b.short_name""", (tender_id,))


def scores(cur, run_ids: list[str], submission_ids: list[str]) -> list[dict]:
    """Final marks of each (run, participant) pair given, pair by pair."""
    return all_rows(cur, """
        select f.score_id::text, f.submission_id::text, c.code, c.max_marks, f.marks,
               f.needs_review, f.reviewed
        from final_score f join criterion c using (criterion_id)
        join unnest(%s::uuid[], %s::uuid[]) as p(run_id, submission_id)
          on p.run_id = f.run_id and p.submission_id = f.submission_id
        order by c.code""", (run_ids, submission_ids))


def manual_marks(cur, criterion_ids: list[str]) -> dict[str, dict[str, object]]:
    """Marks the committee entered for committee-scored criteria:
    {criterion_id: {submission_id: marks}}."""
    rows = all_rows(cur, """select criterion_id::text, submission_id::text, marks
                            from manual_score where criterion_id = any(%s::uuid[])""",
                    (criterion_ids,))
    out: dict[str, dict[str, object]] = {}
    for r in rows:
        out.setdefault(r["criterion_id"], {})[r["submission_id"]] = r["marks"]
    return out


def save_manual_mark(cur, submission_id: str, criterion_id: str, marks, reason: str,
                     user_id: str) -> None:
    """The current mark (manual_score), and the entry in its history (append-only)."""
    cur.execute("""insert into manual_score (submission_id, criterion_id, marks, entered_by)
                   values (%s, %s, %s, %s)
                   on conflict (submission_id, criterion_id) do update
                     set marks = excluded.marks, entered_by = excluded.entered_by,
                         entered_at = now()""", (submission_id, criterion_id, marks, user_id))
    cur.execute("""insert into manual_score_history (submission_id, criterion_id, marks, reason,
                     entered_by)
                   values (%s, %s, %s, %s, %s)""",
                (submission_id, criterion_id, marks, reason, user_id))


def score_detail(cur, score_id: str) -> dict | None:
    return one_row(cur, """
        select s.score_id::text, s.run_id::text, s.submission_id::text, s.criterion_id::text,
               s.llm_marks, s.checked_marks, s.arithmetic_ok, s.needs_review, s.review_reasons,
               s.summary, c.code, c.title, c.max_marks, c.max_items, b.short_name,
               c.allowed_item_marks, c.count_bands, r.tender_id::text, f.marks as final_marks,
               f.reviewed
        from criterion_score s join criterion c using (criterion_id)
        join bid_submission bs on bs.submission_id = s.submission_id
        join bidder b on b.bidder_id = bs.bidder_id
        join evaluation_run r on r.run_id = s.run_id
        join final_score f on f.score_id = s.score_id
        where s.score_id = %s""", (score_id,))


def items(cur, run_id: str, submission_id: str, criterion_id: str) -> list[dict]:
    return all_rows(cur, """
        select i.item_id::text, i.label, i.title, i.kind, i.from_page, i.to_page,
               i.map_confidence, r.eligible, r.counted, r.marks, r.reason, r.count_reason,
               r.confidence, r.facts, r.evidence, r.suspicious_text,
               coalesce(g.mismatches, '{}') as copy_mismatches,
               d.action as decision, d.final_marks as decided_marks, d.reason as decision_reason,
               fi.marks as final_marks, coalesce(fi.counted, false) as final_counted
        from bid_item i left join item_result r using (item_id)
        left join final_item fi on fi.item_id = i.item_id
        left join copy_group g on g.copy_group_id = i.copy_group_id
        left join lateral (select x.action, x.final_marks, x.reason from review_decision x
                           where x.item_id = i.item_id order by x.decided_at desc limit 1) d on true
        where i.run_id = %s and i.submission_id = %s and i.criterion_id = %s
        order by i.from_page""", (run_id, submission_id, criterion_id))


def checks(cur, item_ids: list[str]) -> list[dict]:
    return all_rows(cur, """select item_id::text, fact, pdf_page_no, quote, quote_found,
                                   match_score, parsed_value, value_matches, note
                            from evidence_check where item_id = any(%s::uuid[])
                            order by check_id""", (item_ids,))


def record_decision(cur, score_id: str, item_id: str | None, action: str, marks, reason: str,
                    user_id: str) -> None:
    """item_id None = a decision on the whole criterion (only when it has no items)."""
    cur.execute("""insert into review_decision (score_id, item_id, action, final_marks, reason,
                     reviewer) values (%s, %s, %s, %s, %s, %s)""",
                (score_id, item_id, action, marks, reason, user_id))


def bid_file_key(cur, submission_id: str) -> str | None:
    row = one_row(cur, """select s3_key from submission_file where submission_id = %s
                          order by uploaded_at desc limit 1""", (submission_id,))
    return row["s3_key"] if row else None


def export_items(cur, run_ids: list[str], submission_ids: list[str]) -> list[dict]:
    """Every item claimed in each (run, participant) pair, for the exported sheet: the
    AI's marks, the committee's latest decision and the final marks (final_item)."""
    return all_rows(cur, """
        select i.submission_id::text, c.code, i.title, i.label, i.from_page, i.to_page,
               r.counted, r.eligible, r.marks, coalesce(r.count_reason, r.reason) as reason,
               f.marks as final_marks, f.counted as final_counted,
               d.action, d.reason as decision_reason
        from bid_item i join criterion c using (criterion_id)
        left join item_result r using (item_id)
        left join final_item f on f.item_id = i.item_id
        left join lateral (select x.action, x.reason from review_decision x
                           where x.item_id = i.item_id
                           order by x.decided_at desc limit 1) d on true
        join unnest(%s::uuid[], %s::uuid[]) as p(run_id, submission_id)
          on p.run_id = i.run_id and p.submission_id = i.submission_id
        order by i.submission_id, c.code, i.from_page""", (run_ids, submission_ids))


def export_decisions(cur, score_ids: list[str]) -> list[dict]:
    """Every committee decision on the given scores, oldest first, with the item it was
    about (none for a decision on the whole criterion)."""
    return all_rows(cur, """
        select d.score_id::text, d.action, d.final_marks, d.reason, u.full_name,
               to_char(d.decided_at, 'DD Mon YYYY HH24:MI') as decided,
               i.title, i.label, i.from_page, i.to_page
        from review_decision d join app_user u on u.user_id = d.reviewer
        left join bid_item i on i.item_id = d.item_id
        where d.score_id = any(%s::uuid[]) order by d.decided_at""", (score_ids,))
