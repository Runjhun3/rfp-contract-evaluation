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
| Bid upload per participant | `submission_file` → `page` | text + OCR only, no LLM output |
| "Evaluate" button | `evaluation_run` + `run_submission` + `job` | one run covers the selected bidders |
| Progress bar per bidder | `run_submission.stage`, `items_done/items_total` | |
| Results table | `criterion_score` → views `final_score`, `run_total` | |
| Evidence drawer | `bid_item`, `item_result`, `evidence_check`, `copy_group` | quotes + page links |
| Override / accept | `review_decision` (append-only, reason ≥ 10 chars) | |
| Presentation marks | `manual_score` | 35 marks, entered by committee |

## Shape
```
app_user
tender ─┬─ tender_document
        ├─ criterion
        ├─ evaluation_prompt
        ├─ bid_submission (bidder) ─── submission_file ─── page
        ├─ evaluation_run ─┬─ run_submission (progress per bidder)
        │                  ├─ page_label (LLM labels for this run)
        │                  ├─ copy_group
        │                  ├─ bid_item ─┬─ item_result
        │                  │            └─ evidence_check
        │                  └─ criterion_score ─── review_decision
        ├─ manual_score
        └─ job
views: final_score (review wins over checked marks), run_total (/65 + /35)
```

## Rules the schema enforces
- **Extraction vs judgement.** `page` holds only text/OCR. Anything an LLM
  decided (`page_label`, `bid_item`, `item_result`, `criterion_score`) hangs off
  a `run_id`, so re-running with a new prompt never overwrites old results.
- **Append-only review.** `review_decision` rows are never updated; the latest
  whole-criterion decision wins in `final_score`. A reason of < 10 characters
  is rejected by a CHECK constraint.
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
- `evaluation_run.status`: QUEUED → RUNNING → DONE | FAILED | CANCELLED
- `run_submission.stage`: QUEUED → READING → OCR → LABELLING → ITEMS →
  CHECKS → SCORING → DONE | FAILED

## Not in the first migration
- `page.embedding vector(1024)`: add with pgvector only if meaning-based
  mapping by the LLM proves insufficient (decisions.md D-014).
- Authentication tables: `app_user` is enough until SSO is chosen.

## Loading a CLI run
`python run.py save-run --run <folder> --project "<name>" --user <email>`
loads a finished phase-1 run folder into these tables in one transaction.
It is idempotent: a run already in the database is skipped.
