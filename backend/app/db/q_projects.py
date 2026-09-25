"""Queries for users, projects (tenders), the RFP and its criteria."""
from app.db.connection import all_rows, one_row

PAGE_SIZE = 25


def user_by_email(cur, email: str) -> dict | None:
    return one_row(cur, """select user_id::text, email, full_name, role, password_hash
                           from app_user where lower(email) = lower(%s)""", (email,))


def user_by_id(cur, user_id: str) -> dict | None:
    return one_row(cur, "select user_id::text, full_name, role from app_user where user_id = %s",
                   (user_id,))


def list_projects(cur, page: int) -> list[dict]:
    return all_rows(cur, """
        select t.tender_id::text, t.name, t.gem_bid_no, t.status,
               to_char(t.bid_due_date, 'DD Mon YYYY') as due,
               (select count(*) from bid_submission s where s.tender_id = t.tender_id) as participants,
               (select count(*) from evaluation_run r join final_score f using (run_id)
                 where r.tender_id = t.tender_id and f.needs_review and not f.reviewed) as open_reviews,
               to_char(t.created_at, 'DD Mon YYYY') as created
        from tender t order by t.created_at desc limit %s offset %s""",
        (PAGE_SIZE + 1, (page - 1) * PAGE_SIZE))


def create_project(cur, name: str, gem: str | None, department: str, due: str,
                   user_id: str) -> str:
    row = one_row(cur, """insert into tender (name, gem_bid_no, department, bid_due_date, created_by)
                          values (%s, %s, %s, %s, %s) returning tender_id::text""",
                  (name, gem or None, department, due, user_id))
    return row["tender_id"]


def get_project(cur, tender_id: str) -> dict | None:
    return one_row(cur, """select tender_id::text, name, gem_bid_no, department, status,
                                  bid_due_date::text as bid_due_date,
                                  to_char(bid_due_date, 'DD Mon YYYY') as due
                           from tender where tender_id = %s""", (tender_id,))


def set_status(cur, tender_id: str, status: str) -> None:
    cur.execute("update tender set status = %s where tender_id = %s", (status, tender_id))


def add_rfp(cur, tender_id: str, file_name: str, key: str, sha: str, pages: int,
            user_id: str) -> str:
    row = one_row(cur, """insert into tender_document (tender_id, file_name, s3_key, sha256,
                            page_count, uploaded_by) values (%s, %s, %s, %s, %s, %s)
                          on conflict (tender_id, sha256) do update set file_name = excluded.file_name
                          returning doc_id::text""",
                  (tender_id, file_name, key, sha, pages, user_id))
    return row["doc_id"]


def latest_rfp(cur, tender_id: str) -> dict | None:
    return one_row(cur, """select doc_id::text, file_name, s3_key, page_count,
                                  to_char(uploaded_at, 'DD Mon YYYY HH24:MI') as uploaded
                           from tender_document where tender_id = %s
                           order by uploaded_at desc limit 1""", (tender_id,))


def criteria(cur, tender_id: str) -> list[dict]:
    return all_rows(cur, """
        select criterion_id::text, code, stage, kind, title, rfp_text, meaning,
               trim_scale(max_marks) as max_marks, max_items, scored_by, rfp_page,
               array_to_string(array(select trim_scale(m) from unnest(allowed_item_marks) m),
                               ', ') as allowed
        from criterion where tender_id = %s order by stage desc, code""", (tender_id,))


def update_criterion(cur, criterion_id: str, fields: dict) -> None:
    cur.execute("""update criterion set meaning = %s, kind = %s, max_marks = %s, max_items = %s,
                     allowed_item_marks = %s::numeric[], scored_by = %s where criterion_id = %s""",
                (fields["meaning"], fields["kind"] or None, fields["max_marks"],
                 fields["max_items"], fields["allowed"], fields["scored_by"], criterion_id))


def latest_prompt(cur, tender_id: str) -> dict | None:
    return one_row(cur, """select prompt_id::text, version, criteria_block, status
                           from evaluation_prompt where tender_id = %s
                           order by version desc limit 1""", (tender_id,))


def save_draft_block(cur, tender_id: str, block: str) -> None:
    latest = latest_prompt(cur, tender_id)
    if latest and latest["status"] == "DRAFT":
        cur.execute("update evaluation_prompt set criteria_block = %s where prompt_id = %s",
                    (block, latest["prompt_id"]))
        return
    cur.execute("""insert into evaluation_prompt (tender_id, version, criteria_block, status)
                   select %s, coalesce(max(version), 0) + 1, %s, 'DRAFT'
                   from evaluation_prompt where tender_id = %s""", (tender_id, block, tender_id))


def approve_prompt(cur, tender_id: str, user_id: str) -> None:
    cur.execute("""update evaluation_prompt set status = 'APPROVED', approved_by = %s,
                     approved_at = now()
                   where prompt_id = (select prompt_id from evaluation_prompt where tender_id = %s
                                      order by version desc limit 1)""", (user_id, tender_id))
    set_status(cur, tender_id, "PROMPT_APPROVED")
