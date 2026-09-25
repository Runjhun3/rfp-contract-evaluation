# Schema

PostgreSQL 16 + pgvector. Managed by Alembic. This file is the reference;
the migrations are the source of truth. Update both in the same PR.

## Shape
```
tender ─┬─ tender_document (RFP PDF)
        ├─ criterion (A.1, A.2 ... from Annexure III)
        ├─ evaluation_prompt (criteria block, versioned, approved)
        ├─ bid_submission ─┬─ submission_file ── page
        │                  └─ project (a project or CV, facts read once)
        ├─ evaluation_run ─┬─ claim (project × criterion)
        │                  └─ criterion_score ── review_decision
        ├─ manual_score (presentation marks)
        └─ job (background work queue)
```
Four layers: tender side (what is asked), bid side (what was submitted), run
side (what the LLM decided), review side (what the committee decided).
Nothing is overwritten. Re-runs and reviews add rows.

## Tender side
```sql
create table tender (
  tender_id        uuid primary key,
  gem_bid_no       text unique not null,        -- GEM/2026/B/7401395
  title            text not null,
  department       text,
  selection_method text not null check (selection_method in ('QBS','QCBS','L1')),
  bid_due_at       timestamptz not null,        -- used by date rules
  status           text not null check (status in
                   ('DRAFT','PROMPT_APPROVED','BIDS_RECEIVED','EVALUATING',
                    'COMMITTEE_REVIEW','CLOSED')),
  created_by text not null, created_at timestamptz default now()
);

create table tender_document (                  -- the RFP PDF
  doc_id     uuid primary key,
  tender_id  uuid not null references tender,
  s3_key     text not null,                     -- tenders/<tender_id>/rfp/<sha256>.pdf
  sha256     char(64) not null,
  page_count int,
  created_at timestamptz default now(),
  unique (tender_id, sha256)
);

create table criterion (
  criterion_id uuid primary key,
  tender_id    uuid not null references tender,
  parent_id    uuid references criterion,       -- A -> A.1
  code         text not null,                   -- 'A.1'
  stage        text not null check (stage in ('ELIGIBILITY','TECHNICAL','PRESENTATION')),
  title        text not null,
  rfp_text     text not null,                   -- verbatim clause
  max_marks    numeric(5,2),
  max_items    int,                             -- 8 / 5 / 4; null = no cap
  scored_by    text not null check (scored_by in ('LLM','COMMITTEE')),
  rfp_page     int,
  unique (tender_id, code)
);

create table evaluation_prompt (                -- tender-specific rules, human-approved
  prompt_id      uuid primary key,
  tender_id      uuid not null references tender,
  version        int  not null,
  criteria_block text not null,                 -- rendered from criterion rows, edited by human
  status         text not null check (status in ('DRAFT','APPROVED')),
  approved_by text, approved_at timestamptz,
  unique (tender_id, version)
);
```

## Bid side
```sql
create table bidder (
  bidder_id  uuid primary key,
  legal_name text unique not null,
  short_name text
);

create table bid_submission (
  submission_id uuid primary key,
  tender_id     uuid not null references tender,
  bidder_id     uuid not null references bidder,
  status        text not null check (status in
                ('UPLOADED','INGESTING','INGESTED','FAILED')),
  cover_check   text,                           -- MATCH / MISMATCH / UNKNOWN (bid no. on cover)
  created_at timestamptz default now(),
  unique (tender_id, bidder_id)
);

create table submission_file (
  file_id       uuid primary key,
  submission_id uuid not null references bid_submission,
  s3_key        text not null,                  -- tenders/<tender_id>/bids/<submission_id>/<sha256>.pdf
  sha256        char(64) not null,
  page_count    int,
  pages_done    int not null default 0,         -- resumable ingestion
  unique (submission_id, sha256)
);

create table page (
  page_id          bigserial primary key,
  file_id          uuid not null references submission_file,
  pdf_page_no      int  not null,               -- 1-based; THE page reference
  printed_page_no  text,                        -- display only, unreliable
  text             text,
  extraction       text not null check (extraction in ('TEXT_LAYER','TEXTRACT','VISION')),
  ocr_confidence   numeric(4,3),
  page_type        text,                        -- CLAIM_SUMMARY / PROJECT_HEADER / WORK_ORDER /
                                                -- COMPLETION_CERT / CA_CERT / CV / DECLARATION /
                                                -- MARKETING / BLANK / OTHER
  criterion_hint   text,                        -- 'A.2' read from a page header
  label_prompt_version text,                    -- e.g. page_label_v1
  embedding        vector(1024),                -- nullable; phase 2
  unique (file_id, pdf_page_no)
);

create table project (                          -- one past project or one CV, read once
  project_id      uuid primary key,
  submission_id   uuid not null references bid_submission,
  kind            text not null check (kind in ('PROJECT','CV')),
  label           text not null,                -- bidder's own label, e.g. 'Credential-7'
  claimed_codes   text[] not null,              -- criteria the bidder claims it for, e.g. {A.2,A.3}
  from_pdf_page   int not null,
  to_pdf_page     int not null,
  source          text not null check (source in ('HEADER','SUMMARY','SEARCH','MANUAL')),
  client_name     text,                         -- facts below are filled by the item call
  country         text,
  awarded_on      date,
  start_on date, end_on date,
  duration_months numeric(5,1),
  value_inr       numeric(15,2),
  is_completed    boolean,
  evidence        jsonb,                        -- {"work_order":[285],"completion_or_ca":[306]}
  cv_facts        jsonb                         -- CV only: degree, years, sports/govt experience
);
```

## Run side
```sql
create table evaluation_run (
  run_id           uuid primary key,
  tender_id        uuid not null references tender,
  prompt_id        uuid not null references evaluation_prompt,   -- criteria block version
  prompt_versions  jsonb not null,              -- {"system":"system_v1","item":"item_eval_v1",
                                                --  "criterion":"criterion_eval_v1"}
  model            text not null,               -- CLAUDE_MODEL at run time
  submission_ids   uuid[],                      -- null = all bidders
  status           text not null check (status in ('QUEUED','RUNNING','DONE','FAILED')),
  triggered_by text not null, started_at timestamptz, finished_at timestamptz
);

create table claim (                            -- a project judged under ONE criterion
  claim_id       uuid primary key,
  run_id         uuid not null references evaluation_run,
  project_id     uuid not null references project,
  criterion_id   uuid not null references criterion,
  eligible       boolean not null,
  counted        boolean not null,              -- eligible AND within best N
  marks          numeric(5,2) not null,         -- 0 when not counted
  reason         text not null,
  evidence_pages int[] not null,
  confidence     numeric(4,3) not null,
  unique (run_id, project_id, criterion_id)
);

create table criterion_score (
  score_id       uuid primary key,
  run_id         uuid not null references evaluation_run,
  submission_id  uuid not null references bid_submission,
  criterion_id   uuid not null references criterion,
  llm_marks      numeric(5,2) not null,         -- what the LLM said
  checked_marks  numeric(5,2) not null,         -- Python: sum of counted claim marks, capped
  arithmetic_ok  boolean not null,              -- llm_marks = checked_marks and caps respected
  needs_review   boolean not null,
  review_reasons text[] not null default '{}',  -- ARITHMETIC / LOW_CONFIDENCE / OCR / MISSING_FACT ...
  raw_response   jsonb not null,
  unique (run_id, submission_id, criterion_id)
);
```

## Review side (append-only)
```sql
create table review_decision (
  review_id   uuid primary key,
  score_id    uuid not null references criterion_score,
  claim_id    uuid references claim,            -- null = whole-criterion decision
  action      text not null check (action in
              ('ACCEPT','OVERRIDE','EXCLUDE_CLAIM','INCLUDE_CLAIM')),
  final_marks numeric(5,2),
  reason      text not null check (length(reason) >= 10),
  reviewer    text not null,
  decided_at  timestamptz default now()
);

create table manual_score (                     -- presentation (35 marks)
  submission_id uuid references bid_submission,
  criterion_id  uuid references criterion,
  marks         numeric(5,2) not null,
  entered_by text not null, entered_at timestamptz default now(),
  primary key (submission_id, criterion_id)
);
```

## Job queue
```sql
create table job (
  job_id      bigserial primary key,
  tender_id   uuid not null references tender,
  kind        text not null check (kind in ('INGEST_FILE','OCR_PAGES','LABEL_PAGES',
              'BUILD_PROJECTS','EVAL_ITEM','EVAL_CRITERION','EXTRACT_CRITERIA')),
  ref_id      uuid not null,                    -- file_id / project_id / run_id ...
  status      text not null default 'PENDING' check (status in
              ('PENDING','RUNNING','DONE','FAILED')),
  attempts    int not null default 0,
  last_error  text,
  run_after   timestamptz not null default now(),
  created_at  timestamptz default now(),
  unique (kind, ref_id)                         -- idempotent enqueue
);
-- worker: select ... where status='PENDING' and run_after<=now()
--         order by job_id for update skip locked limit 1
```

## Final marks (view)
The final mark = latest review decision if any, else `checked_marks` from
the run the committee picked.
```sql
create view final_score as
select s.submission_id, s.criterion_id, s.run_id,
       coalesce(r.final_marks, s.checked_marks) as marks,
       r.reviewer, r.reason
from criterion_score s
left join lateral (
  select * from review_decision d
  where d.score_id = s.score_id and d.claim_id is null
  order by d.decided_at desc limit 1) r on true;
```

## Indexes
```sql
create index on page (file_id, page_type);
create index on page using gin (to_tsvector('english', text));
create index on page using hnsw (embedding vector_cosine_ops);  -- phase 2
create index on project (submission_id);
create index on claim (run_id, criterion_id);
create index on job (status, run_after);
```
