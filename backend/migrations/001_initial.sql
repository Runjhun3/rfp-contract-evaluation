-- 001_initial: full schema for the evaluation service. See docs/schema.md.
-- UI "Project" = one GeM tender cycle = table `tender`.
-- Nothing LLM-made is updated in place: every run writes new rows.
-- Needs PostgreSQL 13+ (gen_random_uuid is built in).


-- ================= PEOPLE =================
create table app_user (
  user_id     uuid primary key default gen_random_uuid(),
  email       text unique not null,
  full_name   text not null,
  role        text not null check (role in ('ADMIN','EVALUATOR','COMMITTEE','VIEWER')),
  password_hash text,                                     -- scrypt; null once SSO is used
  is_active   boolean not null default true,
  created_at  timestamptz not null default now()
);

-- ================= PROJECT (TENDER) SIDE =================
create table tender (
  tender_id        uuid primary key default gen_random_uuid(),
  name             text not null,                         -- what the user typed, e.g. "NSDF PMU 2026"
  gem_bid_no       text unique,                           -- GEM/2026/B/7401395 (may be added later)
  department       text,
  bid_due_date     date,                                  -- final closing date, drives date rules
  status           text not null default 'DRAFT' check (status in
                   ('DRAFT','RFP_UPLOADED','CRITERIA_READY','PROMPT_APPROVED',
                    'EVALUATING','REVIEW','CLOSED')),
  created_by       uuid not null references app_user,
  created_at       timestamptz not null default now()
);

create table tender_document (                            -- the RFP PDF
  doc_id      uuid primary key default gen_random_uuid(),
  tender_id   uuid not null references tender on delete cascade,
  file_name   text not null,
  s3_key      text not null,                              -- tenders/<tender_id>/rfp/<sha256>.pdf
  sha256      char(64) not null,
  page_count  int,
  uploaded_by uuid not null references app_user,
  uploaded_at timestamptz not null default now(),
  unique (tender_id, sha256)
);

create table criterion (
  criterion_id       uuid primary key default gen_random_uuid(),
  tender_id          uuid not null references tender on delete cascade,
  code               text not null,                       -- 'A.1'
  parent_code        text,                                -- 'A'
  stage              text not null check (stage in ('ELIGIBILITY','TECHNICAL','PRESENTATION')),
  kind               text check (kind in ('PROJECT','CV')),
  title              text not null,
  rfp_text           text not null,                       -- verbatim clause
  meaning            text not null,                       -- one plain sentence, used for mapping
  max_marks          numeric(6,2),
  max_items          int,
  allowed_item_marks numeric(6,2)[] not null default '{}',
  scored_by          text not null check (scored_by in ('LLM','COMMITTEE')),
  rfp_page           int,
  unique (tender_id, code)
);

create table evaluation_prompt (                          -- human-approved criteria block
  prompt_id      uuid primary key default gen_random_uuid(),
  tender_id      uuid not null references tender on delete cascade,
  version        int not null,
  criteria_block text not null,
  status         text not null check (status in ('DRAFT','APPROVED')),
  approved_by    uuid references app_user,
  approved_at    timestamptz,
  unique (tender_id, version)
);

-- ================= BID SIDE =================
create table bidder (                                     -- master list: EY, Deloitte, GT, PwC ...
  bidder_id  uuid primary key default gen_random_uuid(),
  legal_name text unique not null,
  short_name text not null
);

create table bid_submission (                             -- a bidder selected into a project
  submission_id uuid primary key default gen_random_uuid(),
  tender_id     uuid not null references tender on delete cascade,
  bidder_id     uuid not null references bidder,
  status        text not null default 'AWAITING_FILES' check (status in
                ('AWAITING_FILES','UPLOADED','INGESTING','INGESTED','FAILED')),
  cover_check   text check (cover_check in ('MATCH','MISMATCH','UNKNOWN')),
  created_at    timestamptz not null default now(),
  unique (tender_id, bidder_id)
);

create table submission_file (
  file_id       uuid primary key default gen_random_uuid(),
  submission_id uuid not null references bid_submission on delete cascade,
  file_name     text not null,
  s3_key        text not null,                            -- tenders/<t>/bids/<submission_id>/<sha256>.pdf
  sha256        char(64) not null,
  page_count    int,
  pages_done    int not null default 0,                   -- resumable ingestion
  uploaded_by   uuid not null references app_user,
  uploaded_at   timestamptz not null default now(),
  unique (submission_id, sha256)
);

create table page (                                       -- extraction only; no LLM output here
  page_id        bigserial primary key,
  file_id        uuid not null references submission_file on delete cascade,
  pdf_page_no    int not null,                            -- THE page reference
  text           text not null default '',
  image_ratio    numeric(4,3) not null default 0,
  ocr_text       text,
  extraction     text not null check (extraction in ('TEXT_LAYER','TEXTRACT','TESSERACT')),
  ocr_confidence numeric(4,3),
  unique (file_id, pdf_page_no)
);

-- ================= RUN SIDE (LLM output, append-only) =================
create table evaluation_run (
  run_id          uuid primary key default gen_random_uuid(),
  tender_id       uuid not null references tender on delete cascade,
  prompt_id       uuid not null references evaluation_prompt,   -- criteria block version
  prompt_versions jsonb not null,                   -- {"system":"system_v1","item":"item_eval_v1",...}
  model           text not null,
  status          text not null default 'QUEUED' check (status in
                  ('QUEUED','RUNNING','DONE','FAILED','CANCELLED')),
  error           text,
  triggered_by    uuid not null references app_user,
  created_at      timestamptz not null default now(),
  started_at      timestamptz,
  finished_at     timestamptz
);

create table run_submission (                       -- which bidders a run covers + progress
  run_id        uuid not null references evaluation_run on delete cascade,
  submission_id uuid not null references bid_submission on delete cascade,
  stage         text not null default 'QUEUED' check (stage in
                ('QUEUED','READING','OCR','LABELLING','ITEMS','CHECKS','SCORING','DONE','FAILED')),
  items_total   int not null default 0,
  items_done    int not null default 0,
  error         text,
  primary key (run_id, submission_id)
);

create table page_label (                           -- LLM page labels, per run
  run_id         uuid not null references evaluation_run on delete cascade,
  page_id        bigint not null references page on delete cascade,
  page_type      text not null,
  criterion_code text,
  map_confidence numeric(4,3),
  item_start     boolean not null default false,
  primary key (run_id, page_id)
);

create table copy_group (                           -- same real project under several criteria
  copy_group_id uuid primary key default gen_random_uuid(),
  run_id        uuid not null references evaluation_run on delete cascade,
  submission_id uuid not null references bid_submission on delete cascade,
  mismatches    text[] not null default '{}'        -- e.g. {"value_inr: [...]"}
);

create table bid_item (                             -- one project section or CV, ONE criterion
  item_id        uuid primary key default gen_random_uuid(),
  run_id         uuid not null references evaluation_run on delete cascade,
  submission_id  uuid not null references bid_submission on delete cascade,
  criterion_id   uuid not null references criterion,
  label          text not null,                     -- 'A.1 p.143-148'
  title          text not null default '',
  kind           text not null check (kind in ('PROJECT','CV')),
  map_confidence numeric(4,3) not null,
  from_page      int not null,
  to_page        int not null,
  copy_group_id  uuid references copy_group on delete set null,
  unique (run_id, submission_id, label)
);

create table item_result (                          -- the LLM's judgement of one item
  item_id         uuid primary key references bid_item on delete cascade,
  eligible        boolean not null,
  marks           numeric(6,2) not null,
  counted         boolean,                          -- set by the criterion step (best N)
  count_reason    text,
  reason          text not null,
  confidence      numeric(4,3) not null,
  relies_on       text[] not null default '{}',
  facts           jsonb not null,                   -- {"value_inr":{"value":..,"page":..,"quote":..}}
  evidence        jsonb not null,                   -- {"work_order":[..],"completion_or_ca":[..]}
  cv              jsonb,
  suspicious_text jsonb not null default '[]'
);

create table evidence_check (                       -- Python's verification of each quote
  check_id      bigserial primary key,
  item_id       uuid not null references bid_item on delete cascade,
  fact          text not null,
  pdf_page_no   int,
  quote         text,
  quote_found   boolean not null,
  match_score   int not null default 0,
  parsed_value  text,
  value_matches boolean,
  note          text not null default ''
);

create table criterion_score (
  score_id       uuid primary key default gen_random_uuid(),
  run_id         uuid not null references evaluation_run on delete cascade,
  submission_id  uuid not null references bid_submission on delete cascade,
  criterion_id   uuid not null references criterion,
  llm_marks      numeric(6,2) not null,
  checked_marks  numeric(6,2) not null,             -- Python: sum of counted marks, capped
  arithmetic_ok  boolean not null,
  needs_review   boolean not null,
  review_reasons text[] not null default '{}',
  summary        text not null default '',
  unique (run_id, submission_id, criterion_id)
);

-- ================= REVIEW SIDE (append-only) =================
create table review_decision (
  review_id   uuid primary key default gen_random_uuid(),
  score_id    uuid not null references criterion_score on delete cascade,
  item_id     uuid references bid_item on delete cascade, -- null = whole-criterion decision
  action      text not null check (action in ('ACCEPT','OVERRIDE','EXCLUDE_ITEM','INCLUDE_ITEM')),
  final_marks numeric(6,2),
  reason      text not null check (length(trim(reason)) >= 10),
  reviewer    uuid not null references app_user,
  decided_at  timestamptz not null default now()
);

create table manual_score (                         -- presentation + interview (35 marks)
  submission_id uuid not null references bid_submission on delete cascade,
  criterion_id  uuid not null references criterion,
  marks         numeric(6,2) not null,
  entered_by    uuid not null references app_user,
  entered_at    timestamptz not null default now(),
  primary key (submission_id, criterion_id)
);

-- ================= JOB QUEUE =================
create table job (
  job_id     bigserial primary key,
  tender_id  uuid not null references tender on delete cascade,
  kind       text not null check (kind in ('EXTRACT_CRITERIA','EVALUATE_SUBMISSION')),
  ref_id     uuid not null,                         -- doc_id or (run_id, submission) key below
  run_id     uuid references evaluation_run on delete cascade,
  status     text not null default 'PENDING' check (status in ('PENDING','RUNNING','DONE','FAILED')),
  attempts   int not null default 0,
  last_error text,
  run_after  timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (kind, ref_id, run_id)
);

-- ================= VIEWS =================
-- Final marks: latest whole-criterion review decision, else Python-checked marks.
create view final_score as
select s.run_id, s.submission_id, s.criterion_id, s.score_id,
       coalesce(r.final_marks, s.checked_marks) as marks,
       s.needs_review, (r.review_id is not null) as reviewed, r.reason as review_reason
from criterion_score s
left join lateral (
  select d.* from review_decision d
  where d.score_id = s.score_id and d.item_id is null
  order by d.decided_at desc limit 1) r on true;

-- One row per bidder per run: document marks (/65) + presentation (/35).
create view run_total as
select f.run_id, f.submission_id,
       sum(f.marks) as document_marks,
       coalesce((select sum(m.marks) from manual_score m
                 where m.submission_id = f.submission_id), 0) as presentation_marks,
       bool_or(f.needs_review and not f.reviewed) as open_reviews
from final_score f group by f.run_id, f.submission_id;

-- ================= INDEXES =================
create index on tender_document (tender_id);
create index on criterion (tender_id);
create index on bid_submission (tender_id);
create index on submission_file (submission_id);
create index on page (file_id);
create index on page_label (page_id);
create index on bid_item (run_id, submission_id, criterion_id);
create index on bid_item (copy_group_id);
create index on evidence_check (item_id);
create index on criterion_score (run_id, submission_id);
create index on review_decision (score_id, decided_at desc);
create index on job (status, run_after);
create index on page using gin (to_tsvector('english', coalesce(text, '') || ' ' || coalesce(ocr_text, '')));
