# Local setup

## Prerequisites
- Python 3.12, Docker, AWS access to ap-south-1 (S3, Textract, Bedrock).
- Your own IAM credentials. Never reuse someone else's keys.

## Phase 1: score one bidder (what exists today)
Works from Git Bash or PowerShell on Windows, or any Linux/macOS shell.
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash; PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp ../.env.example ../.env         # fill in your OWN, freshly rotated AWS values
pytest                             # unit tests, no AWS needed

python run.py evaluate \
  --bid "../data/golden/nsdf/Deloitte all docs.pdf" \
  --bidder Deloitte --tender GEM/2026/B/7401395 \
  --department "Department of Sports, MYAS" --bid-date 2026-05-07 \
  --criteria tests/golden/nsdf/criteria.json \
  --block tests/golden/nsdf/criteria_block.md \
  --out runs/nsdf/deloitte

python run.py compare --run runs/nsdf/deloitte --bidder Deloitte \
  --expected tests/golden/nsdf/expected_scores.json
```
- Output: `runs/nsdf/deloitte/comparison.md` + one JSON per step.
- Re-running `evaluate` skips finished steps; delete a step's file to redo it.
- Every LLM answer is cached in `runs/_llm_cache/`; `LLM_MODE=replay` re-runs
  from the cache with no AWS calls.
- No AWS for OCR? Install Tesseract and set `OCR_ENGINE=tesseract`.
- Rough cost per bidder (NSDF, Deloitte): ~25 label calls + ~30 item calls +
  5 criterion calls on Sonnet, and ~250 Textract pages. A few dollars.

## Web UI + worker (full flow)
```bash
cp .env.example .env            # fill in values; never commit .env
docker compose up -d db         # Postgres 16 on localhost:5432
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py migrate           # applies backend/migrations/*.sql
python run.py web               # http://127.0.0.1:8000, no login
python run.py worker            # second terminal: criteria extraction + evaluations
pytest                          # unit tests
pytest -m integration           # full UI flow; needs an EMPTY test database + data/golden/nsdf PDFs
```
No login or roles (decisions.md D-024): the UI opens on Projects and every action
is recorded as "Local user". Keep it on localhost or a private network.

## Environment variables
| Name | Example | Notes |
| ---- | ------- | ----- |
| AWS_REGION | ap-south-1 | |
| S3_BUCKET | rfp-contract-bucke | |
| AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY | — | local only; servers use an IAM role |
| AWS_BEARER_TOKEN_BEDROCK | — | Bedrock API key, local only |
| CLAUDE_MODEL | global.anthropic.claude-sonnet-4-6 | see security.md (data location) |
| DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD | localhost / 5432 / rfp_eval / rfp / — | the container overrides host inside compose |
| LLM_MODE | bedrock | `replay` = use cached answers only, no AWS |
| LLM_CACHE_DIR | runs/_llm_cache | cached LLM answers (audit trail + free re-runs) |
| OCR_ENGINE | textract | `tesseract` for local runs without AWS |
| OCR_MIN_IMAGE_RATIO | 0.25 | image covering this share of a page → OCR |
| SESSION_SECRET | (optional) | signs the CSRF cookie; a random key is made at start if empty |
| COOKIE_SECURE | false | `true` when the UI is served over HTTPS (the VM) |
| FILE_STORE | local | `s3` on the server; uploads go to S3_BUCKET |
| LOCAL_FILE_DIR | data/files | local store, and the cache for S3 files |
| RUNS_DIR | runs | step outputs + page-image cache |
| OCR_MIN_CHARS | 50 | below this a page goes to Textract |
| REVIEW_CONFIDENCE | 0.80 | below this a claim is flagged |

## Running the golden test
```bash
mkdir -p data/golden/nsdf       # copy the 5 NSDF PDFs here (not in git)
pytest -m golden -k nsdf
```

## Common problems
| Symptom | Fix |
| ------- | --- |
| `ThrottlingException` from Bedrock | lower WORKER_CONCURRENCY; the job retries with backoff |
| Textract job stuck IN_PROGRESS | large bundle; the worker polls every 10 s, up to 30 min |
| `vector` type missing | the DB image must be `pgvector/pgvector:pg16` |
