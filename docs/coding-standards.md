# Coding standards

Read alongside architecture.md and local-setup.md in this folder. Root
CLAUDE.md is the index that points here.

## Principles (non-negotiable)
1. Simplest solution that works. No abstraction until there is a second use.
2. One responsibility per file. Files <= 150 lines, functions <= 30 lines.
3. No dead code: no commented-out code, no unused functions, no scratch files
   in app/. If two versions of the same thing exist (e.g. two S3 helpers),
   delete one immediately. Don't leave both "for now".
4. The LLM judges; Python checks every number. The LLM decides eligibility and
   proposes item marks by the rules in the prompt. Python recomputes every
   total, cap and item count from the item list. On any mismatch it sets
   `needs_review = true` and stores both values. It never silently corrects.
   The same goes for evidence: every fact the LLM relies on comes with a
   page and an exact quote, and `evaluate/evidence_check.py` must confirm
   the quote is on that page and states that value/date before the item
   can pass without review.
5. Money is `Decimal` (rupees) — never float. Marks are `Decimal` too.
   Parse with `Decimal(str(x))`, never `Decimal(float)`.
6. Secrets live only in `.env` (git-ignored) locally and in AWS Secrets
   Manager on servers. Never commit, print, or log a secret.
7. Every record links back to one `tender_id`. Every LLM output row also
   carries `run_id`.
8. Pages are referenced by `pdf_page_no` (1-based) only. Never by printed
   page number.
9. Map by meaning. No regex or string matching on RFP headings, annexure
   names or bidder labels to decide which criterion something belongs to.
   The LLM maps against the tender's `criterion.meaning`; code only reads
   the result and its confidence. (Regex is fine for parsing numbers and
   dates inside a verified quote.)
10. Append-only for decisions: never UPDATE or DELETE `claim`,
   `criterion_score` or `review_decision`. A re-run writes new rows.

## Prompt rules
- Every LLM prompt is a separate file in `backend/prompts/`, named
  `<purpose>_v<N>.md` (e.g. `item_eval_v1.md`).
- Code loads the prompt by name. The version string is stored with each
  output (`evaluation_run.prompt_versions`, `page.label_prompt_version`).
- Change a prompt = new file + bump version. Never edit a shipped prompt in
  place. Old prompt versions stay on disk as the audit trail of what
  produced past results. This is different from principle 3: a duplicate
  *module* doing the same job gets deleted, but a superseded prompt *version*
  stays, because `evaluation_run.prompt_versions` can point back to it.
- Tender-specific rules (the criteria block) are data. They are stored in
  `evaluation_prompt.criteria_block` and approved by a human. They are not
  files.
- Every prompt ends with the exact JSON shape to return. Every response is
  parsed into a Pydantic model. Invalid JSON → one retry with the parse
  error appended → then the job fails. Never guess or repair it by hand.
- Placeholders use `{{name}}` and are filled by `llm/prompts.py` only. A
  missing placeholder raises an error.

## Python
- Python 3.12, type hints on every function, `ruff` + `ruff format` clean.
- Pydantic v2 for all API bodies and LLM outputs. SQLAlchemy 2.0 typed ORM.
- No business logic in API route files. Routes call one service function.
- boto3 clients are created once in `app/aws/clients.py`. Nobody else builds
  a client.
- Every Bedrock call goes through `app/llm/bedrock.py` (temperature 0, model
  from settings, prompt caching on the system + criteria block, retries with
  backoff on throttling). Nothing else calls Bedrock.
- Dates are `datetime.date`. Timestamps are timezone-aware UTC.
- Raise specific exceptions. Never `except Exception: pass`.

## Database
- All schema changes go through Alembic migrations. One migration per change.
  Never edit a merged migration.
- Table and column names are snake_case singular (`bid_submission`).
- Every FK is indexed. Every table has `created_at timestamptz default now()`.
- Enum-like columns are `text` with a CHECK constraint, not PG enums, so
  adding a value is a single migration.

## Logging
- Structured JSON logs with `tender_id`, `run_id`, `job_id` where known.
- Never log page text, CV content, prompts with bid text, or secrets. Log
  IDs, counts and timings only.

## Tests
- pytest. Unit tests never call AWS: use recorded LLM responses in
  `tests/fixtures/`.
- The golden test (`tests/golden/`) runs against real Bedrock on demand
  only (`pytest -m golden`), not in every CI run.
- Any change to a prompt or to `evaluate/` must be accompanied by a golden run
  result in the PR description.

## Git
- Branch per change. PR title: `<area>: <what>` (e.g. `ingest: resume OCR`).
- No PDFs, bid data or `.env` in the repo. `.gitignore` covers `*.pdf`,
  `.env`, `data/`.
