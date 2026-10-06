-- 016_audit_trail: the history of what is set up before and around an evaluation
-- (docs/decisions.md D-053). Every table here is append-only: rows are inserted, never
-- updated or deleted (standards rule 10). Who did it is the signed-in account.

-- Each changed field of a criterion: by the committee on the Criteria page, or by a
-- re-extraction of the RFP (edited_by null: the AI). No foreign key to criterion: a
-- row a re-extraction drops is deleted, and its history must stay.
create table if not exists criterion_edit (
  edit_id      bigserial primary key,
  tender_id    uuid not null references tender on delete cascade,
  criterion_id uuid not null,
  code         text not null,
  field        text not null,
  old_value    text,
  new_value    text,
  source       text not null check (source in ('COMMITTEE','EXTRACTION')),
  edited_by    uuid references app_user,
  edited_at    timestamptz not null default now()
);
create index if not exists criterion_edit_tender on criterion_edit (tender_id, edited_at);

-- Every save of a rule text version's text (a draft is edited until approved).
alter table evaluation_prompt add column if not exists created_by uuid references app_user;
create table if not exists prompt_draft_save (
  save_id        bigserial primary key,
  prompt_id      uuid not null references evaluation_prompt on delete cascade,
  criteria_block text not null,
  saved_by       uuid references app_user,   -- null: drafted from an extraction
  saved_at       timestamptz not null default now()
);
create index if not exists prompt_draft_save_prompt on prompt_draft_save (prompt_id, saved_at);

-- What each extraction of the RFP returned, as it came from the AI.
create table if not exists criteria_extraction (
  extraction_id  bigserial primary key,
  tender_id      uuid not null references tender on delete cascade,
  doc_id         uuid not null references tender_document on delete cascade,
  prompt_version text not null,
  model          text not null,
  criteria       jsonb not null,
  general        jsonb not null default '[]',
  extracted_at   timestamptz not null default now()
);
create index if not exists criteria_extraction_tender
  on criteria_extraction (tender_id, extracted_at);

-- Every committee mark entered (manual_score keeps the current one).
create table if not exists manual_score_history (
  history_id    bigserial primary key,
  submission_id uuid not null references bid_submission on delete cascade,
  criterion_id  uuid not null references criterion,
  marks         numeric(6,2) not null,
  reason        text not null default '',
  entered_by    uuid not null references app_user,
  entered_at    timestamptz not null default now()
);
create index if not exists manual_score_history_mark
  on manual_score_history (submission_id, criterion_id, entered_at);

-- The marks entered so far start the history (no reason was asked then).
insert into manual_score_history (submission_id, criterion_id, marks, entered_by, entered_at)
select m.submission_id, m.criterion_id, m.marks, m.entered_by, m.entered_at
from manual_score m
where not exists (select 1 from manual_score_history h
                  where h.submission_id = m.submission_id and h.criterion_id = m.criterion_id);
