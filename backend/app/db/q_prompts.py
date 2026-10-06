"""Queries for the rule text versions (evaluation_prompt) and their saved drafts.
A version is edited while it is a draft and fixed once approved; every save of its
text is kept in prompt_draft_save (migration 016)."""
import json

from app.db.connection import all_rows, one_row
from app.db.q_projects import latest_prompt, set_status


def save_draft_block(cur, tender_id: str, block: str, user_id: str | None) -> None:
    """Save the rule text as the draft version (a new version after an approval).
    user_id None: drafted by an extraction of the RFP. An unchanged draft is not saved."""
    latest = latest_prompt(cur, tender_id)
    if latest and latest["status"] == "DRAFT":
        if latest["criteria_block"] == block:
            return
        cur.execute("update evaluation_prompt set criteria_block = %s where prompt_id = %s",
                    (block, latest["prompt_id"]))
        prompt_id = latest["prompt_id"]
    else:
        prompt_id = one_row(cur, """
            insert into evaluation_prompt (tender_id, version, criteria_block, status, created_by)
            select %s, coalesce(max(version), 0) + 1, %s, 'DRAFT', %s
            from evaluation_prompt where tender_id = %s
            returning prompt_id::text""", (tender_id, block, user_id, tender_id))["prompt_id"]
    cur.execute("""insert into prompt_draft_save (prompt_id, criteria_block, saved_by)
                   values (%s, %s, %s)""", (prompt_id, block, user_id))


def approve_prompt(cur, tender_id: str, user_id: str, criteria: list[dict]) -> None:
    """Approve the latest version, keeping the criteria as they stand (criteria_edits
    .snapshot) next to its rule text."""
    cur.execute("""update evaluation_prompt set status = 'APPROVED', approved_by = %s,
                     approved_at = now(), approved_criteria = %s::jsonb
                   where prompt_id = (select prompt_id from evaluation_prompt where tender_id = %s
                                      order by version desc limit 1)""",
                (user_id, json.dumps(criteria), tender_id))
    set_status(cur, tender_id, "PROMPT_APPROVED")


def approvals(cur, tender_id: str) -> list[dict]:
    """Each approved version, oldest first, with who approved it and the criteria as
    approved (null for approvals before migration 017)."""
    return all_rows(cur, """select p.version, u.full_name,
                                   to_char(p.approved_at, 'DD Mon YYYY HH24:MI') as stamp,
                                   p.approved_criteria
                            from evaluation_prompt p left join app_user u
                              on u.user_id = p.approved_by
                            where p.tender_id = %s and p.status = 'APPROVED'
                            order by p.version""", (tender_id,))
