-- 011_eligibility: eligibility screening before technical evaluation (docs/decisions.md,
-- D-045). The AI checks each eligibility requirement against the pages of a bid that
-- prove it; the committee decides every check; only firms decided as meeting every
-- requirement are evaluated.
--
-- 1. The documents the RFP asks for as proof of an eligibility requirement, which the
--    RFP often lists apart from the requirement itself (criteria_extraction_v4).
alter table criterion add column if not exists proof text;
--    An eligibility row the RFP no longer yields on re-extraction, but that checks refer
--    to (so it cannot be deleted), is retired: kept for the record, no longer screened.
alter table criterion add column if not exists retired boolean not null default false;

-- 2. One AI check of one requirement for one bid file. Append-only: checking again
--    writes new rows, and the latest row per (submission, criterion) is current. Not
--    part of an evaluation run, so the check carries its own prompt version and model.
create table if not exists eligibility_check (
  check_id       uuid primary key default gen_random_uuid(),
  tender_id      uuid not null references tender on delete cascade,
  submission_id  uuid not null references bid_submission on delete cascade,
  criterion_id   uuid not null references criterion,
  file_id        uuid not null references submission_file on delete cascade,
  result         text not null check (result in ('MET','NOT_MET','UNSURE')),
  finding        text not null,
  facts          jsonb not null default '{}',     -- {name: {value, page, quote}}
  verification   jsonb not null default '[]',     -- Python's checks of quotes, values, tests
  pages          int[] not null default '{}',     -- the pages the AI was given
  prompt_version text not null,
  model          text not null,
  checked_at     timestamptz not null default now()
);
create index if not exists eligibility_check_current
  on eligibility_check (submission_id, criterion_id, checked_at desc);

-- 3. The committee's decision on one check. Append-only; the latest one counts. Whether
--    a reason is needed depends on the AI's result, so app/eligibility.py checks it.
create table if not exists eligibility_decision (
  decision_id  uuid primary key default gen_random_uuid(),
  check_id     uuid not null references eligibility_check on delete cascade,
  decision     text not null check (decision in ('MET','NOT_MET')),
  reason       text not null default '',
  reviewer     uuid not null references app_user,
  decided_at   timestamptz not null default now()
);
create index if not exists eligibility_decision_latest
  on eligibility_decision (check_id, decided_at desc);

-- 4. The worker's new job: check one submission's latest bid file (ref_id = submission).
alter table job drop constraint if exists job_kind_check;
alter table job add constraint job_kind_check
  check (kind in ('EXTRACT_CRITERIA','EVALUATE_SUBMISSION','CHECK_ELIGIBILITY'));
