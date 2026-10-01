"""Queries for the firm list, participants (submissions) and their bid files."""
from app.db.connection import all_rows, one_row


# Projects (deleted ones too) holding the firm's bid file, an evaluation or committee
# marks. A firm with any of these stays on record; one merely ticked can be deleted.
_BIDS = """(select count(*) from bid_submission s where s.bidder_id = b.bidder_id
  and (exists (select 1 from submission_file f where f.submission_id = s.submission_id)
       or exists (select 1 from run_submission r where r.submission_id = s.submission_id)
       or exists (select 1 from manual_score m where m.submission_id = s.submission_id))
  ) as bids"""


def bidders(cur, search: str = "") -> list[dict]:
    return all_rows(cur, f"""select b.bidder_id::text, b.legal_name, b.short_name, {_BIDS}
                             from bidder b where b.legal_name ilike %s or b.short_name ilike %s
                             order by b.short_name limit 200""", (f"%{search}%", f"%{search}%"))


def bidder(cur, bidder_id: str) -> dict | None:
    return one_row(cur, f"""select b.bidder_id::text, b.short_name, {_BIDS}
                            from bidder b where b.bidder_id = %s""", (bidder_id,))


def delete_bidder(cur, bidder_id: str) -> None:
    """Only for a firm with no bid or results anywhere (removal.delete_firm checks)."""
    cur.execute("delete from bid_submission where bidder_id = %s", (bidder_id,))
    cur.execute("delete from bidder where bidder_id = %s", (bidder_id,))


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
        where s.tender_id = %s and s.included order by b.short_name""", (tender_id,))


def set_participants(cur, tender_id: str, bidder_ids: list[str]) -> None:
    """Exactly the ticked firms take part. An unticked firm is switched off, never
    deleted: its bid file and past results stay, and ticking it again restores it."""
    for bidder_id in bidder_ids:
        add_participant(cur, tender_id, bidder_id)
    cur.execute("""update bid_submission set included = (bidder_id::text = any(%s::text[]))
                   where tender_id = %s""", (bidder_ids, tender_id))


def add_participant(cur, tender_id: str, bidder_id: str) -> None:
    cur.execute("""insert into bid_submission (tender_id, bidder_id) values (%s, %s)
                   on conflict (tender_id, bidder_id) do update set included = true""",
                (tender_id, bidder_id))


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
