# Architecture

Read alongside coding-standards.md and schema.md. Root CLAUDE.md is the index.

## Build phases
- **Phase 1 (built):** command-line pipeline for one bidder at a time
  (`python run.py evaluate` / `compare`). Each step writes JSON into a run
  folder with the same shapes as schema.md; re-runs skip finished steps.
- **Phase 2 (built):** Postgres (schema.md), the job queue + worker, a JSON
  API (Starlette, `backend/app/web/`, under `/api/v1`) and a React UI
  (React + TypeScript + Vite, `frontend/`; decisions.md D-025). In production
  the Python app serves the built UI from `frontend/dist`. The pipeline still writes its step files under RUNS_DIR as a
  cache and audit trail; results are saved to Postgres when each bidder finishes.

## Components
```
 Committee UI ──HTTP──▶ FastAPI (app/api) ──▶ services ──▶ PostgreSQL + pgvector
                                   │                         ▲
                                   └── enqueue job ──────────┤
                                                             │
                        Worker (app/jobs/worker.py) ─────────┘
                           │        │           │
                           ▼        ▼           ▼
                        Amazon S3  Textract   Bedrock (Claude Sonnet 4.6)
                        rfp-contract-bucke   ap-south-1
```
- **Web process** (`run.py web`): uploads, approvals, run start, review and
  export. It never calls Textract or Bedrock directly. It enqueues jobs.
- **Worker process** (`run.py worker`): pulls one job at a time from the
  `job` table (`FOR UPDATE SKIP LOCKED`). Run 1–4 workers. There is no
  Celery and no Redis.
- **PostgreSQL**: all state, including the job queue.
- **S3**: original PDFs and temporary page bundles for Textract.
- **Textract**: OCR for pages with no text layer.
- **Bedrock**: criteria extraction, page labels, item and criterion evaluation.

## Lifecycle of one tender
```
DRAFT ──(RFP uploaded, criteria extracted, human approves prompt)──▶ PROMPT_APPROVED
PROMPT_APPROVED ──(bids uploaded, days later)──▶ BIDS_RECEIVED
BIDS_RECEIVED ──(all files INGESTED, run started)──▶ EVALUATING
EVALUATING ──(run DONE)──▶ COMMITTEE_REVIEW ──(re-run after prompt fix)──▶ EVALUATING
COMMITTEE_REVIEW ──(presentation marks entered, sheet exported)──▶ CLOSED
```
Days or weeks can pass between steps. All state is in the DB, keyed by
`tender_id`, so nothing is held in memory between steps.

Bids are always uploaded **under** a tender (`POST /tenders/{id}/bids`). The
tender is never inferred from the file. As a second check, the page-label job
reads the cover page and sets `bid_submission.cover_check`.

## Folder layout
```
frontend/                   # React UI: src/pages (one per screen), src/components, src/api.ts; dist/ = build
backend/
  run.py                    # phase 1: `evaluate`, `compare`; phase 2 adds `api|worker|migrate`
  app/
    config.py               # pydantic-settings, reads .env
    api/                    # one file per resource: tenders, bids, runs, reviews, export
    services/               # one file per use case: create_tender, approve_prompt, start_run ...
    db/                     # models.py (split by layer if > 150 lines), session.py
    aws/                    # clients.py, s3.py, textract.py
    llm/                    # bedrock.py (only Bedrock caller), prompts.py (load + fill)
    ingest/                 # split_pages.py, ocr_pages.py, label_pages.py, build_projects.py
    evaluate/               # item_eval.py, evidence_check.py, copy_check.py,
                            # criterion_eval.py, arithmetic_check.py, flags.py
                            # parse_amount.py, parse_date.py (used by evidence_check)
    export/                 # annexure_sheet.py (committee Excel format)
    jobs/                   # queue.py (enqueue/claim/finish), worker.py, handlers.py
    schemas/                # Pydantic models: api bodies + LLM outputs
  prompts/                  # <purpose>_v<N>.md, never edited in place
  migrations/               # numbered plain-SQL files (001_initial.sql ...)
  tests/
    unit/  fixtures/  golden/nsdf/
docs/                       # this folder
docker-compose.yml          # postgres + pgvector for local dev
.env.example
```

## Key libraries
| Need               | Library                        | Note                                   |
| ------------------ | ------------------------------ | -------------------------------------- |
| API                | FastAPI + uvicorn              |                                        |
| Settings           | pydantic-settings              | reads `.env`                           |
| DB                 | psycopg 3, plain SQL           | no ORM; queries live in app/db/        |
| Vectors            | pgvector (python)              | phase 2                                |
| Migrations         | `run.py migrate`               | applies migrations/*.sql in order      |
| PDF text + render  | pypdfium2                      | Apache/BSD licence (avoid AGPL PyMuPDF) |
| AWS                | boto3                          | S3, Textract, bedrock-runtime          |
| Excel export       | openpyxl                       |                                        |
| Fuzzy quote match  | difflib (standard library)     | OCR-tolerant quote check, copy grouping |
| Date parsing       | python-dateutil                | day-first Indian dates                 |
| Tests              | pytest                         |                                        |

## Bedrock usage
- Converse API, `temperature=0`, model from `CLAUDE_MODEL`.
- Prompt caching: a cache point after the system prompt + criteria block,
  because that prefix is identical for every item call in a run.
- Throttling: exponential backoff, at most 5 attempts, then the job fails
  and can be retried from the UI.
- Vision fallback: pages rendered to PNG (pypdfium2, 150 dpi) are sent only
  when Textract confidence < 0.80 on a page cited as evidence.

## Web UI and API (the UI design canvas maps 1:1)
Each React screen (`frontend/src/pages/`) calls the API below. Every reply is
`{"data": ..., "message": ...}`; errors use 4xx with a readable `message`.
Marks are exact strings (Decimal on the server), never JSON numbers.

| Screen (React route) | API (all under /api/v1) |
| ------ | ------ |
| Projects (`/projects?page=N`; `/` redirects here) | GET /projects?page=N |
| New project (`/projects/new`) | POST /projects |
| Open project (`/projects/{id}`) | GET /projects/{id} → `landing` = the step reached |
| 1 Details & RFP (`/projects/{id}/rfp`) | GET /projects/{id}/rfp, POST (multipart) → EXTRACT_CRITERIA job |
| 2 Criteria (`/projects/{id}/criteria`) | GET/POST /projects/{id}/criteria, POST …/criteria/approve; page polls every 10 s until criteria exist |
| 3 Participants & bids (`/projects/{id}/participants?q=`) | GET/POST /projects/{id}/participants, POST /projects/{id}/firms, POST (multipart) /submissions/{id}/file |
| 4 Evaluate (`/runs/{id}`) | POST /projects/{id}/runs → EVALUATE_SUBMISSION jobs; GET /runs/{id}, polled every 5 s until DONE/FAILED |
| 5 Results (`/runs/{id}/results`) | GET /runs/{id}/results, POST /runs/{id}/presentation |
| Evidence (`/scores/{id}?item=&page=`) | GET /scores/{id}?item=, POST /scores/{id}/decision, GET /submissions/{id}/pages/{n}.png |
| (session) | GET /session → the CSRF token |

No login (decisions.md D-024): every action is recorded against the built-in
"Local user". Every POST sends the session's CSRF token in `X-CSRF-Token`.
Any other GET path returns the React app's index.html (client-side routing).
Security headers: CSP `default-src 'self'` (no inline script/style), X-Frame-Options DENY,
nosniff, same-origin referrer, HSTS when COOKIE_SECURE.
