# Schema

PostgreSQL 16 on the same EC2 VM as the service (see deploy-ec2.md).
**Source of truth: `backend/migrations/*.sql`**, applied with
`python run.py migrate`. This page explains the design; change both together.

## How the UI maps to tables
| In the UI | Table | Notes |
| --------- | ----- | ----- |
| Project | `tender` | one GeM tender cycle; name typed by the user |
| RFP upload | `tender_document` | stored in S3, sha256 de-duplicates |
| Criteria (review & approve) | `criterion`, `evaluation_prompt` | approved block is versioned |
| Participants (EY, Deloitte ...) | `bidder` (master list) + `bid_submission` | picking a bidder creates a submission |
| Export "Audit log": participants, firms and jobs | `audit_event` (append-only) + `job.created_by`, `job.cause` | firms ticked/unticked, added, renamed, deleted; every job with who started it and why (017) |
| Bid upload per participant | `submission_file` → `page` | text + OCR only, no LLM output |
| "Evaluate" button | `evaluation_run` + `run_submission` + `job` | one run covers the selected bidders |
| Progress bar per bidder | `run_submission.stage`, `items_done/items_total` | |
| Results table | `criterion_score` → views `final_score`, `run_total` | |
| Evidence drawer | `bid_item`, `item_result`, `evidence_check`, `copy_group` | quotes + page links |
| Override / accept | `review_decision` (append-only, reason ≥ 10 chars) | |
| Eligibility screening | `eligibility_check` → `eligibility_decision` (both append-only) | one AI check per bid file × requirement; the committee decides each |
| Presentation marks | `manual_score` + `manual_score_history` (append-only) | current mark, and every mark entered with who and why it changed |
| Export "Audit log": criteria setup | `criteria_extraction`, `criterion_edit`, `prompt_draft_save`, `evaluation_prompt` (all append-only) | extractions, edited fields, rule text saves and approvals (016) |

## Shape
```
app_user
tender ─┬─ tender_document ─── criteria_extraction (what each extraction returned)
        ├─ criterion
        ├─ criterion_edit (no FK to criterion: history outlives a dropped row)
        ├─ evaluation_prompt ─── prompt_draft_save
        ├─ bid_submission (bidder) ─┬─ submission_file ─── page
        │                           └─ eligibility_check ─── eligibility_decision
        ├─ evaluation_run ─┬─ run_submission (progress per bidder)
        │                  ├─ page_label (LLM labels for this run)
        │                  ├─ copy_group
        │                  ├─ bid_item ─┬─ item_result
        │                  │            └─ evidence_check
        │                  └─ criterion_score ─── review_decision
        ├─ manual_score ─── manual_score_history (per submission × criterion)
        ├─ audit_event (tender_id null: the shared firm list)
        └─ job
views: final_score (review wins over checked marks), run_total (/65 + /35)
```

## Rules the schema enforces
- **Group headings.** A criterion that another row names as its parent is a group
  heading; its total is the plain sum of its sub-criteria. (`group_cap`, added by
  migration 003, was dropped by migration 005; see D-033.)
- **Extraction vs judgement.** `page` holds only text/OCR. Anything an LLM
  decided (`page_label`, `bid_item`, `item_result`, `criterion_score`) hangs off
  a `run_id`, so re-running with a new prompt never overwrites old results.
- **Append-only review.** `review_decision` rows are never updated. Decisions are
  per item (`item_id` set); `final_score` computes a criterion's marks from the
  latest decision on each item (best max-items, capped at max marks). A
  whole-criterion decision (`item_id` null, criteria without items, or made before
  migration 006) wins while it is the latest on the score. An override needs a
  reason of at least 10 characters (CHECK constraint); accepting needs none.
- **Append-only eligibility.** `eligibility_check` rows are never updated: checking
  again writes new rows and the latest per (submission, requirement) is current.
  `eligibility_decision` rows are never updated; the latest per check counts. A check
  is tied to one bid file, so a replaced bid is checked (and decided) afresh.
  `criterion.proof` (011) holds the documents the RFP asks for as proof of an
  eligibility row.
  An eligibility row a re-extraction no longer yields but checks refer to is kept
  with `criterion.retired` = true and is no longer screened or shown.
- **Append-only audit trail (016).** `criterion_edit` has a row per changed field
  (source COMMITTEE, or EXTRACTION with `edited_by` null for the AI);
  `criteria_extraction` keeps each extraction's answer as JSON; `prompt_draft_save`
  keeps every save of a rule text version; `evaluation_prompt.created_by` and
  `approved_by` say who made and approved each version. `manual_score` holds the
  current committee mark and `manual_score_history` every mark entered (a change
  needs a reason). Actors are `app_user` rows: the signed-in account gets its own row
  on first sign-in (`q_users.account`); rows from before 016 point at "Local user".
  `audit_event` (017) records participants and the firm list; its `target` is the
  firm's name at the time and `details.bidder_id` links it, so it outlives a rename
  or deletion. `job.created_by` / `job.cause` say whose action queued each job, and
  `evaluation_prompt.approved_criteria` keeps the criteria as approved.
- **One item, one criterion.** A project repeated under A.1/A.2/A.3 is three
  `bid_item` rows sharing a `copy_group_id`; `copy_group.mismatches` lists
  any disagreement.
- **Money and marks** are `numeric`, read as `Decimal` in Python.
- **Pages** are referenced by `pdf_page_no` only.
- **Status columns** are `text` + CHECK (adding a value = one migration).
- **Deleting a project** cascades to everything under it (bid files in S3 are
  deleted separately by the retention job).

## Status flows
- `tender.status`: DRAFT → RFP_UPLOADED → CRITERIA_READY → PROMPT_APPROVED →
  EVALUATING → REVIEW → CLOSED
- `bid_submission.status`: AWAITING_FILES → UPLOADED → INGESTING → INGESTED | FAILED
- `bid_submission.included` (004): false when the firm is unticked on the participants
  screen. The row is never deleted (it carries the bid file and, through runs, its
  scores); unticked firms are left out of the list, the counts and new runs.
- `tender.deleted_at` (010): set when the project is deleted from the projects list. The
  project is hidden everywhere; no row is removed (D-043). A `bidder` row is deleted
  only when no project holds its bid file, a run or committee marks.
- `criterion.rfp_no` (013): the number the RFP prints for a screened row, shown in place
  of its internal code (E.1), which stays the key (D-047).
- `criterion.considered` (014): an extracted eligibility row is included only when the
  committee chooses to consider it; otherwise it is excluded from all later stages.
- `criterion.source_reference` (015) stores the Annexure/clause location separately
  from the criterion's human-readable title.
- A firm's eligibility is derived, not stored (`app/eligibility.py`): qualified when
  every considered criterion's effective result is met, not qualified when one is not
  met, otherwise open / checking / not checked / check failed. The AI result is effective
  unless the committee records an override; only an AI UNSURE result needs a decision. Only
  qualified firms are evaluated (D-045).
- `evaluation_run.status`: QUEUED → RUNNING → DONE | FAILED | CANCELLED
- `run_submission.stage`: QUEUED → READING → OCR → LABELLING → ITEMS →
  CHECKS → SCORING → DONE | FAILED

## Not in the first migration
- `page.embedding vector(1024)`: add with pgvector only if meaning-based
  mapping by the LLM proves insufficient (decisions.md D-014).
- Authentication: none. `app_user` holds one built-in "Local user" (002_local_user)
  that every action is recorded against (decisions.md D-024).

## Loading a CLI run
`python run.py save-run --run <folder> --project "<name>"`
loads a finished phase-1 run folder into these tables in one transaction.
It is idempotent: a run already in the database is skipped.
