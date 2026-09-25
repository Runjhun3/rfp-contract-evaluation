"""Queries for the results matrix, evidence review and committee decisions."""
from app.db.connection import all_rows, one_row


def scores(cur, run_id: str) -> list[dict]:
    return all_rows(cur, """
        select f.score_id::text, f.submission_id::text, c.code, f.marks, f.needs_review, f.reviewed
        from final_score f join criterion c using (criterion_id)
        where f.run_id = %s order by c.code""", (run_id,))


def scored_criteria(cur, run_id: str) -> list[dict]:
    return all_rows(cur, """select distinct c.code, c.max_marks from criterion_score s
                            join criterion c using (criterion_id) where s.run_id = %s
                            order by c.code""", (run_id,))


def presentation(cur, tender_id: str) -> dict | None:
    return one_row(cur, """select criterion_id::text, code, max_marks from criterion
                           where tender_id = %s and stage = 'PRESENTATION'
                           order by code limit 1""", (tender_id,))


def presentation_marks(cur, criterion_id: str) -> dict[str, object]:
    rows = all_rows(cur, """select submission_id::text, marks from manual_score
                            where criterion_id = %s""", (criterion_id,))
    return {r["submission_id"]: r["marks"] for r in rows}


def save_presentation(cur, submission_id: str, criterion_id: str, marks, user_id: str) -> None:
    cur.execute("""insert into manual_score (submission_id, criterion_id, marks, entered_by)
                   values (%s, %s, %s, %s)
                   on conflict (submission_id, criterion_id) do update
                     set marks = excluded.marks, entered_by = excluded.entered_by,
                         entered_at = now()""", (submission_id, criterion_id, marks, user_id))


def score_detail(cur, score_id: str) -> dict | None:
    return one_row(cur, """
        select s.score_id::text, s.run_id::text, s.submission_id::text, s.criterion_id::text,
               s.llm_marks, s.checked_marks, s.arithmetic_ok, s.needs_review, s.review_reasons,
               s.summary, c.code, c.title, c.max_marks, c.max_items, b.short_name,
               r.tender_id::text, f.marks as final_marks, f.reviewed
        from criterion_score s join criterion c using (criterion_id)
        join bid_submission bs on bs.submission_id = s.submission_id
        join bidder b on b.bidder_id = bs.bidder_id
        join evaluation_run r on r.run_id = s.run_id
        join final_score f on f.score_id = s.score_id
        where s.score_id = %s""", (score_id,))


def items(cur, run_id: str, submission_id: str, criterion_id: str) -> list[dict]:
    return all_rows(cur, """
        select i.item_id::text, i.label, i.title, i.kind, i.from_page, i.to_page,
               r.eligible, r.counted, r.marks, r.reason, r.count_reason, r.confidence,
               r.facts, r.evidence
        from bid_item i left join item_result r using (item_id)
        where i.run_id = %s and i.submission_id = %s and i.criterion_id = %s
        order by i.from_page""", (run_id, submission_id, criterion_id))


def checks(cur, item_id: str) -> list[dict]:
    return all_rows(cur, """select fact, pdf_page_no, quote, quote_found, match_score,
                                   parsed_value, value_matches, note
                            from evidence_check where item_id = %s order by check_id""", (item_id,))


def decisions(cur, score_id: str) -> list[dict]:
    return all_rows(cur, """select d.action, d.final_marks, d.reason, u.full_name,
                                   to_char(d.decided_at, 'DD Mon YYYY HH24:MI') as decided
                            from review_decision d join app_user u on u.user_id = d.reviewer
                            where d.score_id = %s order by d.decided_at desc""", (score_id,))


def record_decision(cur, score_id: str, action: str, marks, reason: str, user_id: str) -> None:
    cur.execute("""insert into review_decision (score_id, action, final_marks, reason, reviewer)
                   values (%s, %s, %s, %s, %s)""", (score_id, action, marks, reason, user_id))


def bid_file_key(cur, submission_id: str) -> str | None:
    row = one_row(cur, """select s3_key from submission_file where submission_id = %s
                          order by uploaded_at desc limit 1""", (submission_id,))
    return row["s3_key"] if row else None
