"""Queries for the firm list, participants (submissions) and their bid files."""
from app.db.connection import all_rows, one_row


def bidders(cur, search: str = "") -> list[dict]:
    return all_rows(cur, """select bidder_id::text, legal_name, short_name from bidder
                            where legal_name ilike %s or short_name ilike %s
                            order by short_name limit 200""", (f"%{search}%", f"%{search}%"))


def add_bidder(cur, legal_name: str, short_name: str) -> str:
    row = one_row(cur, """insert into bidder (legal_name, short_name) values (%s, %s)
                          on conflict (legal_name) do update set short_name = excluded.short_name
                          returning bidder_id::text""", (legal_name, short_name or legal_name))
    return row["bidder_id"]


def submissions(cur, tender_id: str) -> list[dict]:
    return all_rows(cur, """
        select s.submission_id::text, s.bidder_id::text, b.short_name, b.legal_name, s.status,
               s.cover_check, f.file_id::text, f.file_name, f.page_count, f.s3_key,
               to_char(f.uploaded_at, 'DD Mon YYYY HH24:MI') as uploaded
        from bid_submission s join bidder b using (bidder_id)
        left join lateral (select * from submission_file x where x.submission_id = s.submission_id
                           order by x.uploaded_at desc limit 1) f on true
        where s.tender_id = %s order by b.short_name""", (tender_id,))


def set_participants(cur, tender_id: str, bidder_ids: list[str]) -> None:
    """Add newly ticked firms; remove unticked ones that have no bid file yet."""
    for bidder_id in bidder_ids:
        cur.execute("""insert into bid_submission (tender_id, bidder_id) values (%s, %s)
                       on conflict (tender_id, bidder_id) do nothing""", (tender_id, bidder_id))
    cur.execute("""delete from bid_submission s where s.tender_id = %s
                     and not (s.bidder_id::text = any(%s::text[]))
                     and not exists (select 1 from submission_file f
                                     where f.submission_id = s.submission_id)""",
                (tender_id, bidder_ids))


def get_submission(cur, submission_id: str) -> dict | None:
    return one_row(cur, """select s.submission_id::text, s.tender_id::text, b.short_name
                           from bid_submission s join bidder b using (bidder_id)
                           where s.submission_id = %s""", (submission_id,))


def add_file(cur, submission_id: str, file_name: str, key: str, sha: str, pages: int,
             user_id: str) -> None:
    cur.execute("""insert into submission_file (submission_id, file_name, s3_key, sha256,
                     page_count, uploaded_by) values (%s, %s, %s, %s, %s, %s)
                   on conflict (submission_id, sha256) do update
                     set file_name = excluded.file_name, uploaded_at = now()""",
                (submission_id, file_name, key, sha, pages, user_id))
    cur.execute("update bid_submission set status = 'UPLOADED' where submission_id = %s",
                (submission_id,))


def ready_submissions(cur, tender_id: str) -> list[dict]:
    return [s for s in submissions(cur, tender_id) if s["file_id"]]
